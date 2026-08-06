#!/usr/bin/env python3
"""
🦉 OWL-AGENT v4.4 — Advanced ML Predictor
Multiple model backends (Logistic, XGBoost, MLP) with cross-validation
model selection and rich feature engineering.
"""

import asyncio
import time
import logging
from typing import Optional, Dict, Any, List
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import cross_val_score
import joblib

try:
    import xgboost as xgb
    XGB_AVAILABLE = True
except ImportError:
    XGB_AVAILABLE = False

logger = logging.getLogger("owl-agent.ml")

# ─── Model cache directory ──────────────────────────────────
MODEL_DIR = Path.home() / ".owl-agent" / "cache" / "models"
MODEL_DIR.mkdir(parents=True, exist_ok=True)


class AdvancedMLPredictor:
    """Advanced ML predictor with multiple backends and rich features.

    Supports: Logistic Regression, XGBoost, MLP (neural network).
    Automatically selects the best model via cross-validation.
    """

    def __init__(self, model_type: str = "auto", max_samples: int = 2000,
                 retrain_interval: int = 50):
        """
        Args:
            model_type: "auto", "logistic", "xgboost", "mlp"
            max_samples: Max training samples to keep
            retrain_interval: Retrain every N new samples
        """
        self.model_type = model_type
        self.max_samples = max_samples
        self.retrain_interval = retrain_interval
        self._features: List[List[float]] = []
        self._labels: List[int] = []
        self._model = None
        self._scaler = StandardScaler()
        self._is_trained = False
        self._model_name: Optional[str] = None
        self._cv_score: float = 0.0
        self._samples_since_train: int = 0
        self._lock = asyncio.Lock()
        self._training: bool = False

        # Feature names for logging (must match _extract_features output exactly)
        self.feature_names = [
            "fail_count", "healthy", "avg_latency",
            "time_since_success", "is_banned",
            "recent_success_rate",
            "protocol", "country_hash", "url_length",
            "is_post", "hour_of_day", "day_of_week"
        ]

        # Load persisted model if available
        self._load_model()

    def is_trained(self) -> bool:
        return self._is_trained

    @property
    def model_name(self) -> Optional[str]:
        return self._model_name

    @property
    def cv_score(self) -> float:
        return self._cv_score

    def _extract_features(self, proxy_url: str, latency_ms: float,
                          request_context: Optional[Dict] = None,
                          proxy_entry=None) -> List[float]:
        """Extract rich feature vector for proxy success prediction.

        Args:
            proxy_url: Proxy URL string
            latency_ms: Request latency in milliseconds
            request_context: Optional dict with url, method, domain, country
            proxy_entry: Optional ProxyEntry object for real proxy-level data
                (fail_count, healthy, last_check, ban_until)
        """
        ctx = request_context or {}
        f = []

        # --- Proxy-level features (from ProxyEntry when available) ---
        if proxy_entry is not None:
            # Fail count (capped at 100)
            f.append(min(getattr(proxy_entry, 'fail_count', 0), 100) / 100.0)

            # Healthy flag (1.0 if healthy, 0.0 if not)
            f.append(1.0 if getattr(proxy_entry, 'healthy', True) else 0.0)

            # Average latency from scorer history
            avg_lat = ctx.get("avg_latency", latency_ms)
            f.append(avg_lat / 1000.0)

            # Time since last success (seconds since last_check, capped at 300)
            last_check = getattr(proxy_entry, 'last_check', 0.0)
            time_since = min(time.time() - last_check, 300.0) if last_check > 0 else 60.0
            f.append(time_since / 300.0)

            # Is currently banned
            f.append(1.0 if getattr(proxy_entry, 'ban_until', 0.0) > time.time() else 0.0)
        else:
            # Fallback defaults when no ProxyEntry available
            f.append(0.0)   # fail_count
            f.append(1.0)   # healthy (assume yes)
            f.append(latency_ms / 1000.0)  # avg_latency
            f.append(60.0 / 300.0)  # time_since_success
            f.append(0.0)   # is_banned

        # Recent success rate (from scorer)
        recent_success_rate = ctx.get("success_rate", 0.5)
        f.append(recent_success_rate)

        # --- Protocol feature ---
        protocol = proxy_url.split("://")[0] if "://" in proxy_url else "http"
        proto_map = {"http": 0, "https": 1, "socks4": 2, "socks5": 3}
        f.append(proto_map.get(protocol, 0) / 3.0)

        # --- Country feature (hash-based) ---
        country = ctx.get("country", "US")
        f.append((hash(country) % 100) / 100.0)

        # --- Request-level features ---
        url = ctx.get("url", "")
        f.append(min(len(url), 500) / 500.0)  # URL length, capped

        method = ctx.get("method", "GET")
        f.append(1.0 if method == "POST" else 0.0)

        # --- Time features ---
        now = time.localtime()
        f.append(now.tm_hour / 24.0)
        f.append(now.tm_wday / 7.0)

        return f

    async def update(self, proxy_url: str, latency_ms: float, success: bool,
                     request_context: Optional[Dict] = None,
                     scorer=None, proxy_entry=None):
        """Record a new training sample and trigger retraining if needed.

        Args:
            proxy_url: Proxy URL string
            latency_ms: Request latency in milliseconds
            success: Whether the request succeeded
            request_context: Optional dict with url, method, domain, country
            scorer: Optional QualityScorer for success rate data
            proxy_entry: Optional ProxyEntry for real proxy-level features
        """
        # Enrich context with real data from scorer and proxy entry
        ctx = request_context or {}
        if scorer:
            ctx["success_rate"] = scorer.get_recent_success_rate(proxy_url)
            ctx["avg_latency"] = scorer.get_avg_latency(proxy_url)
        if proxy_entry is not None:
            ctx["country"] = ctx.get("country", "US")

        async with self._lock:
            features = self._extract_features(proxy_url, latency_ms, ctx, proxy_entry)
            self._features.append(features)
            self._labels.append(1 if success else 0)

            # Trim to max_samples
            if len(self._features) > self.max_samples:
                self._features = self._features[-self.max_samples:]
                self._labels = self._labels[-self.max_samples:]

            self._samples_since_train += 1

            # Retrain periodically (FIX #4: set _training flag BEFORE to_thread)
            if (len(self._features) >= 50 and
                    self._samples_since_train >= self.retrain_interval):
                self._samples_since_train = 0
                if not self._training:  # Race condition guard
                    self._training = True
                    await asyncio.to_thread(self._train)

    def _train(self):
        """Train models and select the best via cross-validation.

        Respects self.model_type: "auto" trains all candidates, otherwise
        only trains the specified model type. Falls back to Logistic if the
        requested model type is unavailable.
        """
        try:
            X = np.array(self._features)
            y = np.array(self._labels)

            # FIX #3: Minimum sample guard — skip if too few samples
            if len(y) < 10:
                logger.debug(f"Skipping training: only {len(y)} samples (need >= 10)")
                return

            if len(set(y)) < 2:
                logger.debug("Not enough classes for training")
                return

            X_scaled = self._scaler.fit_transform(X)
            best_score = -1
            best_model = None
            best_name = None
            cv = min(3, len(set(y)))  # Cross-validation folds

            # FIX #2: Filter models based on model_type
            # FIX (hardening): fall back to logistic if requested model unavailable
            train_logistic = self.model_type in ("auto", "logistic")
            train_mlp = self.model_type in ("auto", "mlp")
            train_xgb = self.model_type in ("auto", "xgboost") and XGB_AVAILABLE

            if self.model_type == "xgboost" and not XGB_AVAILABLE:
                logger.warning("XGBoost not installed — falling back to Logistic")
                train_logistic = True
            elif self.model_type == "xgboost" and not train_logistic and not train_mlp:
                # Only XGB was requested and it IS available, but we still want a fallback
                train_logistic = True  # Always have logistic as safety net

            # --- Logistic Regression (fast fallback) ---
            if train_logistic:
                try:
                    lr = LogisticRegression(max_iter=1000, class_weight='balanced',
                                            random_state=42)
                    score = cross_val_score(lr, X_scaled, y, cv=cv).mean()
                    if score > best_score:
                        best_score, best_model, best_name = score, lr, "Logistic"
                except Exception as e:
                    logger.debug(f"Logistic training failed: {e}")

            # --- MLP Neural Network ---
            if train_mlp:
                try:
                    mlp = MLPClassifier(
                        hidden_layer_sizes=(64, 32),
                        max_iter=500,
                        early_stopping=True,
                        random_state=42
                    )
                    score = cross_val_score(mlp, X_scaled, y, cv=cv).mean()
                    if score > best_score:
                        best_score, best_model, best_name = score, mlp, "MLP"
                except Exception as e:
                    logger.debug(f"MLP training failed: {e}")

            # --- XGBoost (if available and requested) ---
            if train_xgb:
                try:
                    xgb_model = xgb.XGBClassifier(
                        n_estimators=100,
                        max_depth=4,
                        eval_metric='logloss',
                        random_state=42,
                        use_label_encoder=False
                    )
                    score = cross_val_score(xgb_model, X_scaled, y, cv=cv).mean()
                    if score > best_score:
                        best_score, best_model, best_name = score, xgb_model, "XGBoost"
                except Exception as e:
                    logger.debug(f"XGBoost training failed: {e}")

            if best_model:
                best_model.fit(X_scaled, y)
                self._model = best_model
                self._model_name = best_name
                self._cv_score = best_score
                self._is_trained = True
                logger.info(f"✅ Trained {best_name} model (CV score: {best_score:.3f})")
                self._save_model()

        except Exception as e:
            logger.warning(f"ML training failed: {e}")
        finally:
            self._training = False

    async def predict(self, proxy_url: str, latency_ms: float,
                      request_context: Optional[Dict] = None,
                      scorer=None, proxy_entry=None) -> float:
        """Predict probability of successful request (0.0 - 1.0).

        Args:
            proxy_url: Proxy URL string
            latency_ms: Request latency in milliseconds
            request_context: Optional dict with url, method, domain, country
            scorer: Optional QualityScorer for success rate data
            proxy_entry: Optional ProxyEntry for real proxy-level features
        """
        if not self._is_trained or self._model is None:
            return 0.5

        ctx = request_context or {}
        if scorer:
            ctx["success_rate"] = scorer.get_recent_success_rate(proxy_url)
            ctx["avg_latency"] = scorer.get_avg_latency(proxy_url)

        async with self._lock:
            try:
                features = self._extract_features(proxy_url, latency_ms, ctx, proxy_entry)
                X = np.array([features])
                X_scaled = self._scaler.transform(X)
                prob = self._model.predict_proba(X_scaled)[0][1]
                return float(prob)
            except Exception as e:
                logger.debug(f"Prediction failed: {e}")
                return 0.5

    def _save_model(self):
        """Persist trained model to disk."""
        try:
            path = MODEL_DIR / "proxy_predictor.joblib"
            joblib.dump({
                'model': self._model,
                'scaler': self._scaler,
                'model_name': self._model_name,
                'cv_score': self._cv_score,
            }, path)
            logger.debug(f"Model saved to {path}")
        except Exception as e:
            logger.debug(f"Failed to save model: {e}")

    def _load_model(self):
        """Load persisted model from disk.

        Validates feature dimension to discard stale models that were
        trained with a different feature set (e.g. 11 vs 12 features).
        """
        try:
            path = MODEL_DIR / "proxy_predictor.joblib"
            if path.exists():
                data = joblib.load(path)
                scaler = data.get('scaler')
                model_name = data.get('model_name', 'unknown')

                # Validate feature dimension — discard stale models
                expected_features = len(self.feature_names)
                if scaler is not None and hasattr(scaler, 'n_features_in_'):
                    actual_features = scaler.n_features_in_
                    if actual_features != expected_features:
                        logger.warning(
                            f"Stale model '{model_name}' expects {actual_features} features, "
                            f"but current feature set has {expected_features}. "
                            f"Deleting cached model and retraining later."
                        )
                        path.unlink(missing_ok=True)
                        return

                self._model = data.get('model')
                self._scaler = scaler
                self._model_name = model_name
                self._cv_score = data.get('cv_score', 0.0)
                self._is_trained = True
                logger.info(f"Loaded persisted model: {self._model_name} "
                           f"(CV score: {self._cv_score:.3f})")
        except Exception as e:
            logger.debug(f"Failed to load model: {e}")

    def get_info(self) -> Dict[str, Any]:
        """Return model info for stats endpoint."""
        return {
            "model_name": self._model_name,
            "cv_score": round(self._cv_score, 4),
            "samples": len(self._features),
            "is_trained": self._is_trained,
            "xgboost_available": XGB_AVAILABLE,
        }
