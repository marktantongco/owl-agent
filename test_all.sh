#!/bin/bash
# 🦉 OWL-AGENT Complete Test Suite

echo "═══════════════════════════════════════════════════════════════"
echo "  🦉 OWL-AGENT v4.2 - Complete Test Suite"
echo "═══════════════════════════════════════════════════════════════"
echo ""

PASS=0
FAIL=0

# Test 1: Stats
echo "Test 1: Stats Command"
if ~/.owl-agent/run.sh stats 2>&1 | grep -q "Total proxies:"; then
    echo "  ✓ Stats working"
    PASS=$((PASS+1))
else
    echo "  ✗ Stats failed"
    FAIL=$((FAIL+1))
fi

# Test 2: Direct Fetch
echo "Test 2: Direct Fetch"
if ~/.owl-agent/run.sh fetch https://api.github.com/users/octocat 2>&1 | grep -q '"login"'; then
    echo "  ✓ Direct fetch working"
    PASS=$((PASS+1))
else
    echo "  ✗ Direct fetch failed"
    FAIL=$((FAIL+1))
fi

# Test 3: Proxy Fetch (with fallback)
echo "Test 3: Proxy Fetch (fallback to direct)"
if ~/.owl-agent/run.sh fetch --proxy https://api.github.com/users/octocat 2>&1 | grep -q '"login"'; then
    echo "  ✓ Proxy fetch working (with fallback)"
    PASS=$((PASS+1))
else
    echo "  ✗ Proxy fetch failed"
    FAIL=$((FAIL+1))
fi

# Test 4: Help
echo "Test 4: Help Command"
if ~/.owl-agent/run.sh help 2>&1 | grep -q "Commands:"; then
    echo "  ✓ Help working"
    PASS=$((PASS+1))
else
    echo "  ✗ Help failed"
    FAIL=$((FAIL+1))
fi

# Test 5: Mock Demo
echo "Test 5: Mock Demo"
if python3 ~/.owl-agent/mock_demo.py 2>&1 | grep -q "All tools simulated"; then
    echo "  ✓ Mock demo working"
    PASS=$((PASS+1))
else
    echo "  ✗ Mock demo failed"
    FAIL=$((FAIL+1))
fi

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  Results: $PASS passed, $FAIL failed"
echo "═══════════════════════════════════════════════════════════════"

if [ $FAIL -eq 0 ]; then
    echo "  ✓ ALL TESTS PASSED!"
else
    echo "  ⚠ Some tests failed"
fi
