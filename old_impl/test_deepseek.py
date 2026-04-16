"""
Test script to check DeepSeek API connection with SSL fix
"""
import os
import sys
import ssl

# Remove SSL_CERT_FILE if set (can cause issues)
if "SSL_CERT_FILE" in os.environ:
    print(f"Removing SSL_CERT_FILE: {os.environ['SSL_CERT_FILE']}")
    del os.environ["SSL_CERT_FILE"]

if "REQUESTS_CA_BUNDLE" in os.environ:
    print(f"Removing REQUESTS_CA_BUNDLE: {os.environ['REQUESTS_CA_BUNDLE']}")
    del os.environ["REQUESTS_CA_BUNDLE"]

import httpx
from openai import OpenAI

# DeepSeek API configuration
API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
BASE_URL = "https://api.deepseek.com"
MODEL = "deepseek-chat"

def test_with_ssl_disabled():
    """Test with SSL verification disabled"""
    print("=" * 50)
    print("Test 1: httpx with SSL verification DISABLED")
    print("=" * 50)
    
    try:
        # Create client with SSL verification disabled
        response = httpx.get(f"{BASE_URL}", timeout=10.0, verify=False)
        print(f"✓ Basic connectivity OK - Status: {response.status_code}")
    except Exception as e:
        print(f"✗ Basic connectivity failed: {type(e).__name__}: {e}")
        return False
    
    return True

def test_openai_with_ssl_disabled():
    """Test OpenAI client with SSL verification disabled"""
    print("\n" + "=" * 50)
    print("Test 2: OpenAI client with SSL verification DISABLED")
    print("=" * 50)
    
    try:
        # Create httpx client with SSL verification disabled
        http_client = httpx.Client(verify=False)
        
        client = OpenAI(
            api_key=API_KEY,
            base_url=BASE_URL,
            http_client=http_client
        )
        
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": "Say 'Hello' in one word"}],
            max_tokens=10,
            stream=False
        )
        
        print(f"✓ Success! Response: {response.choices[0].message.content}")
        return True
    except Exception as e:
        print(f"✗ Failed: {type(e).__name__}: {e}")
        return False

def test_streaming_with_ssl_disabled():
    """Test streaming response with SSL verification disabled"""
    print("\n" + "=" * 50)
    print("Test 3: Streaming response with SSL verification DISABLED")
    print("=" * 50)
    
    try:
        # Create httpx client with SSL verification disabled
        http_client = httpx.Client(verify=False)
        
        client = OpenAI(
            api_key=API_KEY,
            base_url=BASE_URL,
            http_client=http_client
        )
        
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": "Count from 1 to 5"}],
            max_tokens=50,
            stream=True
        )
        
        print("✓ Streaming response: ", end="")
        for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                print(chunk.choices[0].delta.content, end="", flush=True)
        print("\n✓ Streaming completed!")
        return True
    except Exception as e:
        print(f"✗ Failed: {type(e).__name__}: {e}")
        return False

if __name__ == "__main__":
    import warnings
    # Suppress SSL warnings for testing
    warnings.filterwarnings('ignore', message='Unverified HTTPS request')
    
    print("DeepSeek API Connection Test (SSL Fix)")
    print("Python version:", sys.version)
    print()
    
    ssl_works = test_with_ssl_disabled()
    
    if ssl_works:
        openai_works = test_openai_with_ssl_disabled()
        if openai_works:
            test_streaming_with_ssl_disabled()
    
    print("\n" + "=" * 50)
    print("CONCLUSION:")
    print("=" * 50)
    if ssl_works:
        print("✓ The issue is SSL certificate verification.")
        print("  Solution: Disable SSL verification in httpx.Client")
        print("  Use: httpx.Client(verify=False)")
    else:
        print("✗ Network connectivity issue - check firewall/proxy settings")
