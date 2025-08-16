#!/usr/bin/env python3
"""
SkipTheQueue Performance Test Suite
Tests the performance optimizations implemented for 500+ concurrent users
"""

import requests
import time
import threading
import statistics
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urljoin
import sys

class PerformanceTester:
    def __init__(self, base_url='http://localhost:8000'):
        self.base_url = base_url
        self.results = {
            'page_load_times': [],
            'api_response_times': [],
            'concurrent_users': [],
            'errors': [],
            'cache_hits': 0,
            'cache_misses': 0
        }
        self.session = requests.Session()
        
    def test_page_load(self, url_path, expected_time=2.0):
        """Test page load performance"""
        start_time = time.time()
        try:
            response = self.session.get(urljoin(self.base_url, url_path))
            load_time = time.time() - start_time
            
            self.results['page_load_times'].append({
                'url': url_path,
                'time': load_time,
                'status': response.status_code,
                'size': len(response.content)
            })
            
            # Check performance headers
            if 'X-Response-Time' in response.headers:
                server_time = float(response.headers['X-Response-Time'].replace('s', ''))
                self.results['api_response_times'].append(server_time)
            
            if 'X-Cache-Status' in response.headers:
                if response.headers['X-Cache-Status'] == 'HIT':
                    self.results['cache_hits'] += 1
                else:
                    self.results['cache_misses'] += 1
            
            if load_time > expected_time:
                print(f"⚠ Slow page load: {url_path} took {load_time:.2f}s")
            
            return load_time
            
        except Exception as e:
            self.results['errors'].append(f"Error loading {url_path}: {str(e)}")
            return None
    
    def test_api_endpoint(self, endpoint, method='GET', data=None, expected_time=1.0):
        """Test API endpoint performance"""
        start_time = time.time()
        try:
            if method == 'GET':
                response = self.session.get(urljoin(self.base_url, endpoint))
            elif method == 'POST':
                response = self.session.post(urljoin(self.base_url, endpoint), json=data)
            
            api_time = time.time() - start_time
            
            self.results['api_response_times'].append({
                'endpoint': endpoint,
                'method': method,
                'time': api_time,
                'status': response.status_code
            })
            
            if api_time > expected_time:
                print(f"⚠ Slow API: {endpoint} took {api_time:.2f}s")
            
            return api_time
            
        except Exception as e:
            self.results['errors'].append(f"Error testing API {endpoint}: {str(e)}")
            return None
    
    def test_concurrent_users(self, num_users=50, test_duration=30):
        """Test concurrent user performance"""
        print(f"Testing {num_users} concurrent users for {test_duration} seconds...")
        
        def user_simulation(user_id):
            """Simulate a single user's behavior"""
            user_results = []
            start_time = time.time()
            
            while time.time() - start_time < test_duration:
                # Simulate user browsing
                pages = ['/', '/menu/', '/help/', '/college/gh-raisoni/']
                
                for page in pages:
                    load_time = self.test_page_load(page)
                    if load_time:
                        user_results.append(load_time)
                    
                    # Simulate user think time
                    time.sleep(0.5)
            
            return user_results
        
        # Run concurrent users
        with ThreadPoolExecutor(max_workers=num_users) as executor:
            futures = [executor.submit(user_simulation, i) for i in range(num_users)]
            
            for future in as_completed(futures):
                try:
                    user_times = future.result()
                    self.results['concurrent_users'].extend(user_times)
                except Exception as e:
                    self.results['errors'].append(f"Concurrent user error: {str(e)}")
    
    def test_database_performance(self):
        """Test database query performance"""
        print("Testing database performance...")
        
        # Test common database operations
        db_tests = [
            ('/api/menu/', 'Menu items query'),
            ('/api/colleges/', 'Colleges query'),
            ('/api/orders/', 'Orders query'),
        ]
        
        for endpoint, description in db_tests:
            times = []
            for _ in range(10):  # Test 10 times
                start_time = time.time()
                response = self.session.get(urljoin(self.base_url, endpoint))
                query_time = time.time() - start_time
                times.append(query_time)
            
            avg_time = statistics.mean(times)
            max_time = max(times)
            min_time = min(times)
            
            print(f"{description}:")
            print(f"  Average: {avg_time:.3f}s")
            print(f"  Min: {min_time:.3f}s")
            print(f"  Max: {max_time:.3f}s")
            
            if avg_time > 0.5:
                print(f"  ⚠ {description} is slow!")
    
    def test_caching_performance(self):
        """Test caching performance"""
        print("Testing caching performance...")
        
        # Test cache hit rates
        cache_test_urls = ['/', '/menu/', '/help/']
        
        for url in cache_test_urls:
            # First request (cache miss)
            start_time = time.time()
            response1 = self.session.get(urljoin(self.base_url, url))
            first_load = time.time() - start_time
            
            # Second request (should be cache hit)
            start_time = time.time()
            response2 = self.session.get(urljoin(self.base_url, url))
            second_load = time.time() - start_time
            
            improvement = ((first_load - second_load) / first_load) * 100
            
            print(f"{url}:")
            print(f"  First load: {first_load:.3f}s")
            print(f"  Second load: {second_load:.3f}s")
            print(f"  Improvement: {improvement:.1f}%")
            
            if improvement < 50:
                print(f"  ⚠ Caching not working effectively for {url}")
    
    def test_javascript_performance(self):
        """Test JavaScript performance optimizations"""
        print("Testing JavaScript performance...")
        
        # Test pages with JavaScript
        js_pages = [
            '/canteen/dashboard/gh-raisoni/',
            '/menu/',
            '/cart/',
        ]
        
        for page in js_pages:
            try:
                response = self.session.get(urljoin(self.base_url, page))
                
                # Check for inline scripts (should be minimal)
                content = response.text
                inline_scripts = content.count('<script>')
                
                if inline_scripts > 2:
                    print(f"⚠ Too many inline scripts on {page}: {inline_scripts}")
                else:
                    print(f"✓ Good: {page} has {inline_scripts} inline scripts")
                
                # Check for external scripts
                external_scripts = content.count('<script src=')
                print(f"  External scripts: {external_scripts}")
                
            except Exception as e:
                print(f"Error testing {page}: {e}")
    
    def generate_report(self):
        """Generate comprehensive performance report"""
        print("\n" + "="*60)
        print("SKIPTHEQUEUE PERFORMANCE TEST REPORT")
        print("="*60)
        
        # Page load performance
        if self.results['page_load_times']:
            times = [r['time'] for r in self.results['page_load_times']]
            avg_load_time = statistics.mean(times)
            max_load_time = max(times)
            min_load_time = min(times)
            
            print(f"\n📄 PAGE LOAD PERFORMANCE:")
            print(f"  Average: {avg_load_time:.3f}s")
            print(f"  Min: {min_load_time:.3f}s")
            print(f"  Max: {max_load_time:.3f}s")
            print(f"  Total pages tested: {len(times)}")
            
            # Performance rating
            if avg_load_time < 1.0:
                print("  ✅ EXCELLENT - Page loads are very fast!")
            elif avg_load_time < 2.0:
                print("  ✅ GOOD - Page loads are acceptable")
            elif avg_load_time < 3.0:
                print("  ⚠ ACCEPTABLE - Page loads could be faster")
            else:
                print("  ❌ POOR - Page loads are too slow")
        
        # API performance
        if self.results['api_response_times']:
            if isinstance(self.results['api_response_times'][0], dict):
                api_times = [r['time'] for r in self.results['api_response_times']]
            else:
                api_times = self.results['api_response_times']
            
            avg_api_time = statistics.mean(api_times)
            max_api_time = max(api_times)
            
            print(f"\n🔌 API PERFORMANCE:")
            print(f"  Average: {avg_api_time:.3f}s")
            print(f"  Max: {max_api_time:.3f}s")
            print(f"  Total API calls: {len(api_times)}")
            
            if avg_api_time < 0.5:
                print("  ✅ EXCELLENT - API responses are very fast!")
            elif avg_api_time < 1.0:
                print("  ✅ GOOD - API responses are acceptable")
            else:
                print("  ⚠ SLOW - API responses need optimization")
        
        # Concurrent user performance
        if self.results['concurrent_users']:
            concurrent_times = self.results['concurrent_users']
            avg_concurrent = statistics.mean(concurrent_times)
            max_concurrent = max(concurrent_times)
            
            print(f"\n👥 CONCURRENT USER PERFORMANCE:")
            print(f"  Average response time: {avg_concurrent:.3f}s")
            print(f"  Max response time: {max_concurrent:.3f}s")
            print(f"  Total requests: {len(concurrent_times)}")
            
            if avg_concurrent < 1.0:
                print("  ✅ EXCELLENT - Handles concurrent users well!")
            elif avg_concurrent < 2.0:
                print("  ✅ GOOD - Acceptable concurrent performance")
            else:
                print("  ⚠ POOR - Struggles with concurrent users")
        
        # Caching performance
        total_cache_requests = self.results['cache_hits'] + self.results['cache_misses']
        if total_cache_requests > 0:
            cache_hit_rate = (self.results['cache_hits'] / total_cache_requests) * 100
            
            print(f"\n💾 CACHING PERFORMANCE:")
            print(f"  Cache hits: {self.results['cache_hits']}")
            print(f"  Cache misses: {self.results['cache_misses']}")
            print(f"  Hit rate: {cache_hit_rate:.1f}%")
            
            if cache_hit_rate > 70:
                print("  ✅ EXCELLENT - High cache hit rate!")
            elif cache_hit_rate > 50:
                print("  ✅ GOOD - Decent cache hit rate")
            else:
                print("  ⚠ POOR - Low cache hit rate")
        
        # Error summary
        if self.results['errors']:
            print(f"\n❌ ERRORS ({len(self.results['errors'])}):")
            for error in self.results['errors'][:5]:  # Show first 5 errors
                print(f"  - {error}")
            if len(self.results['errors']) > 5:
                print(f"  ... and {len(self.results['errors']) - 5} more errors")
        
        # Overall assessment
        print(f"\n🎯 OVERALL ASSESSMENT:")
        
        # Calculate overall score
        score = 0
        max_score = 100
        
        # Page load score (30 points)
        if self.results['page_load_times']:
            avg_load = statistics.mean([r['time'] for r in self.results['page_load_times']])
            if avg_load < 1.0:
                score += 30
            elif avg_load < 2.0:
                score += 20
            elif avg_load < 3.0:
                score += 10
        
        # API score (25 points)
        if self.results['api_response_times']:
            if isinstance(self.results['api_response_times'][0], dict):
                avg_api = statistics.mean([r['time'] for r in self.results['api_response_times']])
            else:
                avg_api = statistics.mean(self.results['api_response_times'])
            
            if avg_api < 0.5:
                score += 25
            elif avg_api < 1.0:
                score += 20
            elif avg_api < 2.0:
                score += 10
        
        # Concurrent user score (25 points)
        if self.results['concurrent_users']:
            avg_concurrent = statistics.mean(self.results['concurrent_users'])
            if avg_concurrent < 1.0:
                score += 25
            elif avg_concurrent < 2.0:
                score += 20
            elif avg_concurrent < 3.0:
                score += 10
        
        # Cache score (20 points)
        total_cache = self.results['cache_hits'] + self.results['cache_misses']
        if total_cache > 0:
            hit_rate = (self.results['cache_hits'] / total_cache) * 100
            if hit_rate > 70:
                score += 20
            elif hit_rate > 50:
                score += 15
            elif hit_rate > 30:
                score += 10
        
        # Error penalty
        error_penalty = min(len(self.results['errors']) * 2, 20)
        score = max(0, score - error_penalty)
        
        print(f"  Performance Score: {score}/{max_score}")
        
        if score >= 80:
            print("  🏆 EXCELLENT - Ready for 500+ concurrent users!")
        elif score >= 60:
            print("  ✅ GOOD - Can handle moderate load")
        elif score >= 40:
            print("  ⚠ ACCEPTABLE - Needs some optimization")
        else:
            print("  ❌ POOR - Significant optimization needed")
        
        print("\n" + "="*60)
        
        # Save detailed results
        with open('performance_test_results.json', 'w') as f:
            json.dump(self.results, f, indent=2)
        
        print("Detailed results saved to: performance_test_results.json")


def main():
    """Main test runner"""
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    else:
        base_url = 'http://localhost:8000'
    
    print(f"Starting performance tests against: {base_url}")
    print("Make sure your Django server is running!")
    
    tester = PerformanceTester(base_url)
    
    try:
        # Basic page load tests
        print("\n1. Testing basic page loads...")
        pages = ['/', '/menu/', '/help/', '/college/gh-raisoni/']
        for page in pages:
            tester.test_page_load(page)
        
        # API performance tests
        print("\n2. Testing API endpoints...")
        api_endpoints = [
            '/api/menu/',
            '/api/colleges/',
            '/api/cart-count/',
        ]
        for endpoint in api_endpoints:
            tester.test_api_endpoint(endpoint)
        
        # Database performance tests
        print("\n3. Testing database performance...")
        tester.test_database_performance()
        
        # Caching performance tests
        print("\n4. Testing caching performance...")
        tester.test_caching_performance()
        
        # JavaScript performance tests
        print("\n5. Testing JavaScript optimizations...")
        tester.test_javascript_performance()
        
        # Concurrent user tests
        print("\n6. Testing concurrent users...")
        tester.test_concurrent_users(num_users=20, test_duration=10)
        
        # Generate report
        tester.generate_report()
        
    except KeyboardInterrupt:
        print("\n⚠ Tests interrupted by user")
        tester.generate_report()
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        tester.generate_report()


if __name__ == '__main__':
    main()
