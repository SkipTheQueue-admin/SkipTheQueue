#!/usr/bin/env python3
"""
Performance Testing Script for SkipTheQueue
This script tests various aspects of the application performance
"""

import time
import requests
import sqlite3
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
import statistics

# Configuration
BASE_URL = "http://localhost:8000"  # Change this to your server URL
TEST_ENDPOINTS = [
    "/",
    "/menu/",
    "/cart/",
    "/favorites/",
    "/order-history/",
    "/help-center/",
]

class PerformanceTester:
    def __init__(self, base_url=BASE_URL):
        self.base_url = base_url
        self.results = {}
        
    def test_endpoint_performance(self, endpoint):
        """Test performance of a single endpoint"""
        url = f"{self.base_url}{endpoint}"
        response_times = []
        
        print(f"Testing {endpoint}...")
        
        # Test multiple requests
        for i in range(5):
            start_time = time.time()
            try:
                response = requests.get(url, timeout=30)
                end_time = time.time()
                
                if response.status_code == 200:
                    response_time = (end_time - start_time) * 1000  # Convert to milliseconds
                    response_times.append(response_time)
                    print(f"  Request {i+1}: {response_time:.2f}ms")
                else:
                    print(f"  Request {i+1}: Failed with status {response.status_code}")
                    
            except requests.exceptions.RequestException as e:
                print(f"  Request {i+1}: Error - {e}")
        
        if response_times:
            avg_time = statistics.mean(response_times)
            min_time = min(response_times)
            max_time = max(response_times)
            
            self.results[endpoint] = {
                'avg_response_time': avg_time,
                'min_response_time': min_time,
                'max_response_time': max_time,
                'success_rate': len(response_times) / 5 * 100
            }
            
            print(f"  Results: Avg={avg_time:.2f}ms, Min={min_time:.2f}ms, Max={max_time:.2f}ms")
        else:
            print(f"  No successful requests for {endpoint}")
    
    def test_concurrent_performance(self, endpoint, concurrent_users=10):
        """Test performance under concurrent load"""
        url = f"{self.base_url}{endpoint}"
        print(f"Testing {endpoint} with {concurrent_users} concurrent users...")
        
        def make_request():
            start_time = time.time()
            try:
                response = requests.get(url, timeout=30)
                end_time = time.time()
                return (end_time - start_time) * 1000, response.status_code == 200
            except:
                return None, False
        
        response_times = []
        success_count = 0
        
        with ThreadPoolExecutor(max_workers=concurrent_users) as executor:
            futures = [executor.submit(make_request) for _ in range(concurrent_users)]
            
            for future in as_completed(futures):
                response_time, success = future.result()
                if response_time is not None:
                    response_times.append(response_time)
                    if success:
                        success_count += 1
        
        if response_times:
            avg_time = statistics.mean(response_times)
            min_time = min(response_times)
            max_time = max(response_times)
            success_rate = success_count / concurrent_users * 100
            
            print(f"  Concurrent Test Results:")
            print(f"    Avg Response Time: {avg_time:.2f}ms")
            print(f"    Min Response Time: {min_time:.2f}ms")
            print(f"    Max Response Time: {max_time:.2f}ms")
            print(f"    Success Rate: {success_rate:.1f}%")
            
            return {
                'avg_response_time': avg_time,
                'min_response_time': min_time,
                'max_response_time': max_time,
                'success_rate': success_rate,
                'concurrent_users': concurrent_users
            }
        
        return None
    
    def test_database_performance(self):
        """Test database performance"""
        print("Testing database performance...")
        
        db_path = "db.sqlite3"
        if not os.path.exists(db_path):
            print("  Database file not found")
            return None
        
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Test simple query performance
            start_time = time.time()
            cursor.execute("SELECT COUNT(*) FROM orders_order")
            count = cursor.fetchone()[0]
            end_time = time.time()
            
            simple_query_time = (end_time - start_time) * 1000
            
            # Test complex query performance
            start_time = time.time()
            cursor.execute("""
                SELECT o.id, o.status, o.total_price, c.name as college_name
                FROM orders_order o
                JOIN orders_college c ON o.college_id = c.id
                WHERE o.status = 'Pending'
                ORDER BY o.created_at DESC
                LIMIT 10
            """)
            results = cursor.fetchall()
            end_time = time.time()
            
            complex_query_time = (end_time - start_time) * 1000
            
            # Test index usage
            start_time = time.time()
            cursor.execute("PRAGMA index_list(orders_order)")
            indexes = cursor.fetchall()
            end_time = time.time()
            
            index_check_time = (end_time - start_time) * 1000
            
            conn.close()
            
            print(f"  Database Test Results:")
            print(f"    Simple Query: {simple_query_time:.2f}ms")
            print(f"    Complex Query: {complex_query_time:.2f}ms")
            print(f"    Index Check: {index_check_time:.2f}ms")
            print(f"    Total Orders: {count}")
            print(f"    Indexes Found: {len(indexes)}")
            
            return {
                'simple_query_time': simple_query_time,
                'complex_query_time': complex_query_time,
                'index_check_time': index_check_time,
                'total_orders': count,
                'index_count': len(indexes)
            }
            
        except Exception as e:
            print(f"  Database test failed: {e}")
            return None
    
    def test_cache_performance(self):
        """Test cache performance"""
        print("Testing cache performance...")
        
        try:
            # Test cache hit/miss scenarios
            cache_times = []
            
            # Simulate cache operations
            for i in range(10):
                start_time = time.time()
                
                # Simulate cache lookup
                cache_key = f"test_key_{i}"
                # In a real scenario, this would interact with Django's cache
                
                end_time = time.time()
                cache_times.append((end_time - start_time) * 1000)
            
            avg_cache_time = statistics.mean(cache_times)
            print(f"  Cache Test Results:")
            print(f"    Average Cache Operation: {avg_cache_time:.2f}ms")
            
            return {
                'avg_cache_time': avg_cache_time,
                'cache_operations': len(cache_times)
            }
            
        except Exception as e:
            print(f"  Cache test failed: {e}")
            return None
    
    def run_all_tests(self):
        """Run all performance tests"""
        print("🚀 Starting Performance Tests for SkipTheQueue")
        print("=" * 60)
        
        # Test individual endpoints
        print("\n📊 Testing Individual Endpoints")
        print("-" * 40)
        for endpoint in TEST_ENDPOINTS:
            self.test_endpoint_performance(endpoint)
        
        # Test concurrent performance
        print("\n🔥 Testing Concurrent Performance")
        print("-" * 40)
        concurrent_results = {}
        for endpoint in TEST_ENDPOINTS[:3]:  # Test first 3 endpoints
            result = self.test_concurrent_performance(endpoint, concurrent_users=5)
            if result:
                concurrent_results[endpoint] = result
        
        # Test database performance
        print("\n🗄️  Testing Database Performance")
        print("-" * 40)
        db_results = self.test_database_performance()
        
        # Test cache performance
        print("\n💾 Testing Cache Performance")
        print("-" * 40)
        cache_results = self.test_cache_performance()
        
        # Generate performance report
        self.generate_report(concurrent_results, db_results, cache_results)
    
    def generate_report(self, concurrent_results, db_results, cache_results):
        """Generate a comprehensive performance report"""
        print("\n📈 Performance Report")
        print("=" * 60)
        
        # Endpoint performance summary
        print("\n🌐 Endpoint Performance Summary:")
        for endpoint, results in self.results.items():
            print(f"  {endpoint}:")
            print(f"    Average Response Time: {results['avg_response_time']:.2f}ms")
            print(f"    Success Rate: {results['success_rate']:.1f}%")
        
        # Concurrent performance summary
        if concurrent_results:
            print("\n⚡ Concurrent Performance Summary:")
            for endpoint, results in concurrent_results.items():
                print(f"  {endpoint} ({results['concurrent_users']} users):")
                print(f"    Average Response Time: {results['avg_response_time']:.2f}ms")
                print(f"    Success Rate: {results['success_rate']:.1f}%")
        
        # Database performance summary
        if db_results:
            print("\n🗄️  Database Performance Summary:")
            print(f"  Simple Query: {db_results['simple_query_time']:.2f}ms")
            print(f"  Complex Query: {db_results['complex_query_time']:.2f}ms")
            print(f"  Total Orders: {db_results['total_orders']}")
            print(f"  Indexes: {db_results['index_count']}")
        
        # Cache performance summary
        if cache_results:
            print("\n💾 Cache Performance Summary:")
            print(f"  Average Cache Operation: {cache_results['avg_cache_time']:.2f}ms")
        
        # Performance recommendations
        self.generate_recommendations()
    
    def generate_recommendations(self):
        """Generate performance improvement recommendations"""
        print("\n💡 Performance Recommendations:")
        print("-" * 40)
        
        # Analyze results and provide recommendations
        slow_endpoints = []
        for endpoint, results in self.results.items():
            if results['avg_response_time'] > 1000:  # More than 1 second
                slow_endpoints.append(endpoint)
        
        if slow_endpoints:
            print("  🐌 Slow Endpoints Detected:")
            for endpoint in slow_endpoints:
                print(f"    - {endpoint}: Consider adding caching or optimization")
        
        # Database recommendations
        if hasattr(self, 'db_results') and self.db_results:
            if self.db_results['complex_query_time'] > 100:
                print("  🗄️  Database Optimization Needed:")
                print("    - Consider adding database indexes")
                print("    - Optimize complex queries")
                print("    - Use select_related and prefetch_related")
        
        # General recommendations
        print("  🚀 General Performance Tips:")
        print("    - Enable Django caching")
        print("    - Use CDN for static files")
        print("    - Optimize images and compress assets")
        print("    - Implement database connection pooling")
        print("    - Use async operations where possible")
        print("    - Monitor and log performance metrics")

def main():
    """Main function to run performance tests"""
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    else:
        base_url = BASE_URL
    
    tester = PerformanceTester(base_url)
    
    try:
        tester.run_all_tests()
    except KeyboardInterrupt:
        print("\n\n⚠️  Performance testing interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Performance testing failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
