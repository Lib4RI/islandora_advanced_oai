#!/usr/bin/env python3
"""
Dashboard Dev Server & Proxy
=============================
Starts a local HTTP server for the OAI-PMH Dashboard and provides
a local CORS proxy to bypass browser security policies restricting
JavaScript from fetching data from internal dev servers.
"""

import http.server
import socketserver
import urllib.request
import urllib.parse
import ssl
import sys
import subprocess
import os
import glob

PORT = 8080

class ProxyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        # Determine base path for comparison endpoints (strip query string)
        base_path = self.path.split('?')[0]
        
        # Intercept Proxy Routing requests
        if base_path == '/proxy':
            # Parse target url from query
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            target_url = qs.get('url', [''])[0]
            if not target_url:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"No 'url' parameter provided to proxy.")
                return
            
            try:
                # Setup SSL context (bypassing cert validation for dev servers)
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                
                req = urllib.request.Request(target_url, headers={'User-Agent': 'Local-Dashboard-Proxy/1.0'})
                with urllib.request.urlopen(req, context=ctx, timeout=30) as response:
                    content = response.read()
                    
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/xml; charset=utf-8')
                    # Set permissive CORS headers for the local UI
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(content)
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'text/plain; charset=utf-8')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(f"Proxy Internal Error: {str(e)}".encode('utf-8'))
        elif base_path == '/run-compare':
            try:
                # Parse query params
                qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                fresh = qs.get('fresh', ['false'])[0].lower() == 'true'
                
                # If fresh, clear caches
                if fresh:
                    print("Cleaning up OAI harvest caches...")
                    for f in glob.glob(".harvest_cache_*.json"):
                        try:
                            os.remove(f)
                            print(f"  Removed {f}")
                        except Exception as e:
                            print(f"  Error removing {f}: {e}")

                # Execute compare_oai.py
                print("Starting OAI Comparison Script...")
                # We use the same python interpreter that's running the server
                # Use a larger timeout for long-running harvest
                result = subprocess.run(
                    [sys.executable, 'compare_oai.py'],
                    capture_output=True,
                    text=True,
                    timeout=600 # 10 minute timeout
                )
                
                output = f"STDOUT:\n{result.stdout}\n\nSTDERR:\n{result.stderr}"
                
                status_code = 200 if result.returncode == 0 else 500
                self.send_response(status_code)
                self.send_header('Content-Type', 'text/plain; charset=utf-8')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(output.encode('utf-8'))
                print(f"Comparison script finished with return code {result.returncode}")
                
            except subprocess.TimeoutExpired:
                self.send_response(504)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(b"Error: Comparison script timed out after 10 minutes.")
            except Exception as e:
                self.send_response(500)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(f"Error executing comparison: {str(e)}".encode('utf-8'))
        elif base_path == '/report':
            try:
                report_path = 'comparison_results.txt'
                if os.path.exists(report_path):
                    with open(report_path, 'rb') as f:
                        content = f.read()
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/plain; charset=utf-8')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(content)
                else:
                    self.send_response(404)
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(b"Report not found. Please run compare_oai.py first.")
            except Exception as e:
                self.send_response(500)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(f"Error reading report: {str(e)}".encode('utf-8'))
        elif base_path == '/architecture':
            try:
                arch_path = 'oai2a_architecture.md'
                if os.path.exists(arch_path):
                    with open(arch_path, 'rb') as f:
                        content = f.read()
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/markdown; charset=utf-8')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(content)
                else:
                    self.send_response(404)
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(b"Architecture documentation file not found in current directory.")
            except Exception as e:
                self.send_response(500)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(f"Error reading architecture: {str(e)}".encode('utf-8'))
        elif base_path == '/favicon.ico':
            self.send_response(404)
            self.end_headers()
        else:
            # Fallback to serving static HTML files
            return super().do_GET()

if __name__ == '__main__':
    with socketserver.TCPServer(("", PORT), ProxyHTTPRequestHandler) as httpd:
        print(f"===========================================================")
        print(f"Dashboard Hub Server running locally on port {PORT}")
        print(f"1. Open your browser and go to:")
        print(f"   http://localhost:{PORT}/oai_dashboard.html")
        print(f"2. Kepp this terminal running to serve as the proxy.")
        print(f"===========================================================")
        print("Press Ctrl+C to shut down.")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down Server...")
            sys.exit(0)
