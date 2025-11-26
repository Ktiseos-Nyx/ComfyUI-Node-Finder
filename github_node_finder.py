"""
GitHub Node Finder

Searches GitHub for ComfyUI custom node repositories based on node class names.
"""

import requests
import json
import time
import subprocess
import webbrowser
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from workflow_parser import WorkflowParser
from token_manager import TokenManager
from comfyui_scanner import ComfyUIScanner


class GitHubNodeFinder:
    """Find GitHub repositories for ComfyUI node classes."""
    
    REGISTRY_URL = "https://raw.githubusercontent.com/ltdrdata/ComfyUI-Manager/main/custom-node-list.json"
    COMFY_REGISTRY_API = "https://api.comfy.org/nodes"
    
    def __init__(self, github_token: str):
        """
        Initialize the GitHub node finder.
        
        Args:
            github_token: GitHub personal access token (REQUIRED for code search)
                         Create one at: https://github.com/settings/tokens
                         Needs 'public_repo' or 'repo' scope
        """
        if not github_token:
            raise ValueError(
                "GitHub token is required for code search API.\n"
                "Create a token at: https://github.com/settings/tokens\n"
                "Required scopes: 'public_repo' or 'repo'"
            )
        
        self.github_token = github_token
        self.base_url = "https://api.github.com"
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"token {github_token}"
        }
        
        # Cache to avoid duplicate searches
        self.cache = {}
        
        # ComfyUI Manager registry cache (old format)
        self.registry = None
        self.registry_by_title = {}
        self.registry_by_reference = {}
        
        # Comfy Registry API cache (new format - all nodes)
        self.comfy_registry = []
        self.comfy_registry_loaded = False
    
    def load_comfyui_registry(self) -> bool:
        """
        Load the ComfyUI Manager registry of custom nodes.
        
        Returns:
            True if loaded successfully
        """
        if self.registry is not None:
            return True  # Already loaded
        
        try:
            print("📥 Loading ComfyUI Manager registry...")
            response = requests.get(self.REGISTRY_URL, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                self.registry = data.get('custom_nodes', [])
                
                # Build lookup dictionaries
                for node in self.registry:
                    title = node.get('title', '').lower()
                    reference = node.get('reference', '').lower()
                    
                    if title:
                        self.registry_by_title[title] = node
                    if reference:
                        self.registry_by_reference[reference] = node
                
                print(f"✓ Loaded {len(self.registry)} custom nodes from registry")
                return True
            else:
                print(f"⚠ Failed to load registry: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            print(f"⚠ Error loading registry: {e}")
            return False
    
    def load_comfy_registry_all(self) -> bool:
        """
        Load ALL nodes from the Comfy Registry API (paginated).
        
        Returns:
            True if loaded successfully
        """
        if self.comfy_registry_loaded:
            return True  # Already loaded
        
        try:
            print("📥 Loading Comfy Registry (all nodes)...")
            all_nodes = []
            page = 1
            limit = 100  # Max per page
            
            while True:
                params = {
                    'page': page,
                    'limit': limit
                }
                
                response = requests.get(self.COMFY_REGISTRY_API, params=params, timeout=30)
                
                if response.status_code == 200:
                    data = response.json()
                    nodes = data.get('nodes', [])
                    
                    if not nodes:
                        break  # No more nodes
                    
                    all_nodes.extend(nodes)
                    
                    total_pages = data.get('totalPages', 1)
                    print(f"   Loaded page {page}/{total_pages} ({len(all_nodes)} nodes so far)...")
                    
                    if page >= total_pages:
                        break
                    
                    page += 1
                    
                    # Add delay between pages to be nice to the API
                    if page <= total_pages:
                        time.sleep(0.5)
                else:
                    print(f"⚠ Failed to load Comfy Registry: HTTP {response.status_code}")
                    return False
            
            self.comfy_registry = all_nodes
            self.comfy_registry_loaded = True
            print(f"✓ Loaded {len(all_nodes)} nodes from Comfy Registry")
            return True
            
        except Exception as e:
            print(f"⚠ Error loading Comfy Registry: {e}")
            return False
    
    def search_in_registry(self, class_name: str) -> Optional[Dict]:
        """
        Search for a node in the Comfy Registry (all nodes loaded locally).
        
        Args:
            class_name: The node class name to search for
            
        Returns:
            Dictionary with repository info or None if not found
        """
        # Load all registry data once
        if not self.load_comfy_registry_all():
            return None
        
        class_lower = class_name.lower()
        
        # Search through all loaded nodes
        for node in self.comfy_registry:
            name = node.get('name', '').lower()
            description = node.get('description', '').lower()
            node_id = node.get('id', '').lower()
            
            # Check if class name appears in name, description, or ID
            if (class_lower in name or 
                class_lower in description or 
                class_lower in node_id):
                
                return {
                    'repo_name': node.get('repository', '').split('/')[-1] if node.get('repository') else node.get('id', ''),
                    'repo_url': node.get('repository', ''),
                    'description': node.get('description', ''),
                    'author': node.get('publisher', {}).get('name', 'unknown') if isinstance(node.get('publisher'), dict) else 'unknown',
                    'title': node.get('name', class_name),
                    'downloads': node.get('downloads', 0),
                    'stars': node.get('github_stars', 0)
                }
        
        return None
    
    def search_node_class(self, class_name: str) -> Optional[Dict]:
        """
        Search for a ComfyUI node class, first in registry then GitHub.
        
        Args:
            class_name: The node class name to search for
            
        Returns:
            Dictionary with repository info or None if not found
        """
        # Check cache first
        if class_name in self.cache:
            return self.cache[class_name]
        
        # Try ComfyUI Manager registry first (no rate limits!)
        registry_result = self.search_in_registry(class_name)
        if registry_result:
            self.cache[class_name] = registry_result
            return registry_result
        
        # Search GitHub code for the class name
        search_query = f"{class_name} comfyui"
        url = f"{self.base_url}/search/code"
        params = {
            "q": search_query,
            "per_page": 5
        }
        
        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            
            if response.status_code == 401:
                print(f"  ⚠ Authentication failed. Check your GitHub token.")
                print(f"     Token must have 'public_repo' or 'repo' scope.")
                print(f"     Create/update at: https://github.com/settings/tokens")
                return None
            
            if response.status_code == 403:
                # Check if it's rate limit or token issue
                if 'X-RateLimit-Remaining' in response.headers:
                    remaining = response.headers['X-RateLimit-Remaining']
                    limit = response.headers.get('X-RateLimit-Limit', 'unknown')
                    reset_timestamp = response.headers.get('X-RateLimit-Reset')
                    
                    print(f"  ⚠ Rate limit exceeded!")
                    print(f"     Search API Limit: {limit} requests per minute")
                    print(f"     Remaining: {remaining}")
                    
                    if reset_timestamp and remaining == '0':
                        # Calculate wait time
                        reset_time = int(reset_timestamp)
                        current_time = int(time.time())
                        wait_seconds = reset_time - current_time + 5  # Add 5 second buffer
                        
                        if wait_seconds > 0:
                            print(f"     Waiting {wait_seconds} seconds until reset...")
                            # Show countdown for long waits
                            if wait_seconds > 10:
                                for remaining_time in range(wait_seconds, 0, -10):
                                    print(f"     ... {remaining_time} seconds remaining")
                                    time.sleep(10)
                                # Sleep any remaining seconds
                                time.sleep(wait_seconds % 10)
                            else:
                                time.sleep(wait_seconds)
                            print(f"  ✓ Rate limit reset. Retrying search...")
                            # Retry the request
                            return self.search_node_class(class_name)
                        else:
                            print(f"  ⚠ Rate limit should be reset. Retrying...")
                            return self.search_node_class(class_name)
                    else:
                        print(f"     Try again in a minute.")
                        return None
                else:
                    print(f"  ⚠ Access forbidden. Check your GitHub token permissions.")
                return None
            
            if response.status_code != 200:
                print(f"  ⚠ GitHub API error: {response.status_code}")
                if response.status_code == 422:
                    print(f"     Search query may be invalid or too complex")
                return None
            
            data = response.json()
            
            if data.get("total_count", 0) == 0:
                # Try alternative search without "comfyui"
                return self._search_alternative(class_name)
            
            # Get the first result
            for item in data.get("items", []):
                repo_info = self._extract_repo_info(item, class_name)
                if repo_info:
                    self.cache[class_name] = repo_info
                    return repo_info
            
            return None
            
        except requests.exceptions.RequestException as e:
            print(f"  ⚠ Network error: {e}")
            return None
    
    def _search_alternative(self, class_name: str) -> Optional[Dict]:
        """Alternative search strategy without 'comfyui' keyword."""
        url = f"{self.base_url}/search/code"
        params = {
            "q": f'"{class_name}" language:python',
            "per_page": 5
        }
        
        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                for item in data.get("items", []):
                    repo_info = self._extract_repo_info(item, class_name)
                    if repo_info:
                        return repo_info
        except:
            pass
        
        return None
    
    def _extract_repo_info(self, item: Dict, class_name: str) -> Optional[Dict]:
        """Extract repository information from search result."""
        repo = item.get("repository", {})
        
        # Handle None repository
        if not repo:
            return None
        
        # Filter for likely ComfyUI repos
        repo_name = repo.get("full_name", "")
        repo_desc = repo.get("description", "")
        
        if not repo_name:
            return None
        
        repo_name = repo_name.lower()
        repo_desc = repo_desc.lower() if repo_desc else ""
        
        # Check if it's likely a ComfyUI custom node repo
        if "comfy" in repo_name or "comfy" in repo_desc:
            return {
                "class_name": class_name,
                "repo_name": repo.get("full_name"),
                "repo_url": repo.get("html_url"),
                "description": repo.get("description", "No description"),
                "stars": repo.get("stargazers_count", 0),
                "file_path": item.get("path"),
                "file_url": item.get("html_url")
            }
        
        return None
    
    def search_all_nodes(self, nodes: Dict[str, Dict], scanner: Optional[ComfyUIScanner] = None) -> Dict[str, Optional[Dict]]:
        """
        Search GitHub for all unique node classes in a workflow.
        
        Args:
            nodes: Dictionary of nodes from WorkflowParser
            scanner: Optional ComfyUIScanner to identify built-in/custom nodes
            
        Returns:
            Dictionary mapping class names to repository info
        """
        # Get unique class types
        class_types = set(node_info['class_type'] for node_info in nodes.values())
        
        # Use scanner if provided, otherwise use hardcoded list
        if scanner and scanner.comfyui_path:
            builtin_nodes = scanner.builtin_nodes
            known_custom = scanner.custom_nodes
            
            # Separate nodes by classification
            nodes_to_search = set()
            builtin_found = set()
            custom_found = {}
            
            for class_name in class_types:
                classification = scanner.classify_node(class_name)
                if classification == 'builtin':
                    builtin_found.add(class_name)
                elif classification == 'custom':
                    repo_name = scanner.get_custom_node_repo(class_name)
                    custom_found[class_name] = repo_name
                else:
                    nodes_to_search.add(class_name)
            
            print(f"\n📊 Node Classification:")
            print(f"   Built-in nodes: {len(builtin_found)}")
            print(f"   Known custom nodes: {len(custom_found)}")
            print(f"   Unknown nodes (will search GitHub): {len(nodes_to_search)}")
            
            if custom_found:
                print(f"\n📦 Custom nodes already installed:")
                repos = {}
                for node, repo in custom_found.items():
                    if repo not in repos:
                        repos[repo] = []
                    repos[repo].append(node)
                for repo, node_list in sorted(repos.items()):
                    print(f"   {repo}: {', '.join(node_list)}")
        else:
            # Fallback to hardcoded list
            builtin_nodes = {
                'KSampler', 'CheckpointLoaderSimple', 'CLIPTextEncode', 'VAEDecode',
                'VAEEncode', 'EmptyLatentImage', 'LoadImage', 'SaveImage', 'PreviewImage',
                'VAELoader', 'LoraLoader', 'CLIPLoader', 'ControlNetLoader',
                'LatentUpscale', 'ImageScale', 'UpscaleModelLoader', 'ImageUpscaleWithModel',
                'PrimitiveNode', 'Reroute', 'Note', 'BasicGuider', 'BasicScheduler',
                'KSamplerSelect', 'RandomNoise', 'SamplerCustomAdvanced'
            }
            nodes_to_search = class_types - builtin_nodes
            builtin_found = builtin_nodes & class_types
            custom_found = {}
            
            print(f"\n🔍 Searching GitHub for {len(nodes_to_search)} node classes...")
            print(f"   (Skipping {len(builtin_found)} built-in nodes)")
        
        if not nodes_to_search:
            print(f"\n✓ All nodes are already identified!")
            return {}
        
        print(f"\n🔍 Searching GitHub for {len(nodes_to_search)} unknown nodes...\n")
        
        results = {}
        
        # Add known custom nodes to results
        for class_name, repo_name in custom_found.items():
            results[class_name] = {
                "class_name": class_name,
                "repo_name": repo_name,
                "repo_url": f"(local installation: {repo_name})",
                "description": "Already installed locally",
                "stars": 0,
                "file_path": "local",
                "file_url": "local"
            }
        
        # Search GitHub for unknown nodes
        for i, class_name in enumerate(sorted(nodes_to_search), 1):
            print(f"[{i}/{len(nodes_to_search)}] Searching for: {class_name}")
            
            result = self.search_node_class(class_name)
            results[class_name] = result
            
            if result:
                print(f"  ✓ Found: {result['repo_url']}")
            else:
                print(f"  ✗ Not found")
            
            # Rate limiting: be nice to GitHub
            time.sleep(1)
        
        return results
    
    def clone_repository(self, repo_url: str, destination: Path) -> bool:
        """
        Clone a GitHub repository using git.
        
        Args:
            repo_url: GitHub repository URL
            destination: Destination path for the clone
            
        Returns:
            True if successful
        """
        try:
            print(f"\n📥 Cloning {repo_url}...")
            result = subprocess.run(
                ['git', 'clone', repo_url, str(destination)],
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode == 0:
                print(f"✓ Successfully cloned to {destination}")
                return True
            else:
                print(f"✗ Failed to clone: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            print(f"✗ Clone timed out after 5 minutes")
            return False
        except FileNotFoundError:
            print(f"✗ Git not found. Please install git: https://git-scm.com/")
            return False
        except Exception as e:
            print(f"✗ Error cloning repository: {e}")
            return False
    
    def handle_found_repos(self, results: Dict[str, Optional[Dict]], comfyui_path: Optional[str] = None) -> bool:
        """
        Prompt user to download or open found repositories.
        
        Args:
            results: Dictionary of search results
            comfyui_path: Optional path to ComfyUI installation
            
        Returns:
            True if repositories were downloaded
        """
        # Filter to only repos found on GitHub (not local)
        github_repos = {
            k: v for k, v in results.items() 
            if v is not None and not v['repo_url'].startswith('(local')
        }
        
        if not github_repos:
            print("\n✓ No new repositories to download")
            return False
        
        # Group by repository
        repos_by_url = {}
        for class_name, info in github_repos.items():
            repo_url = info['repo_url']
            if repo_url not in repos_by_url:
                repos_by_url[repo_url] = {
                    'repo_name': info['repo_name'],
                    'description': info.get('description', 'No description'),
                    'stars': info.get('stars', 0),
                    'nodes': []
                }
            repos_by_url[repo_url]['nodes'].append(class_name)
        
        print(f"\n{'=' * 80}")
        print(f"FOUND {len(repos_by_url)} REPOSITORIES")
        print(f"{'=' * 80}\n")
        
        for i, (repo_url, repo_info) in enumerate(sorted(repos_by_url.items()), 1):
            stars_display = f"⭐ {repo_info['stars']}" if repo_info['stars'] > 0 else ""
            print(f"{i}. {repo_info['repo_name']} {stars_display}")
            print(f"   {repo_info['description']}")
            print(f"   Nodes: {', '.join(repo_info['nodes'])}")
            print(f"   URL: {repo_url}\n")
        
        # Ask to download
        download = input("Download these repositories? (y/n) [n]: ").strip().lower()
        
        if download == 'y':
            # Determine destination
            if comfyui_path:
                custom_nodes_dir = Path(comfyui_path) / "custom_nodes"
                if custom_nodes_dir.exists():
                    dest_dir = custom_nodes_dir
                    print(f"\n📁 Will clone to: {dest_dir}")
                else:
                    print(f"\n⚠ custom_nodes not found, aborting download.")
                    return
            else:
                print(f"\n⚠ No ComfyUI path found, aborting download.")
                return
            
            confirm = input("Continue? (y/n) [y]: ").strip().lower() or 'y'
            
            if confirm == 'y':
                repos_cloned = False
                for repo_url, repo_info in repos_by_url.items():
                    repo_name = repo_info['repo_name'].split('/')[-1]
                    destination = dest_dir / repo_name
                    
                    if destination.exists():
                        print(f"\n⚠ {repo_name} already exists, skipping...")
                        continue
                    
                    if self.clone_repository(repo_url, destination):
                        repos_cloned = True
                    time.sleep(1)  # Be nice to GitHub
                
                print(f"\n✓ Download complete!")
                return repos_cloned
            
            return False
        
        # Ask to open in browser
        open_browser = input("\nOpen repositories in browser? (y/n) [n]: ").strip().lower()
        
        if open_browser == 'y':
            print("\n🌐 Opening repositories in browser...")
            for repo_url in repos_by_url.keys():
                try:
                    webbrowser.open(repo_url)
                    time.sleep(0.5)  # Small delay between opens
                except Exception as e:
                    print(f"✗ Failed to open {repo_url}: {e}")
            print("✓ Done!")
        
        return False  # No repos were downloaded
    
    def save_results(self, results: Dict[str, Optional[Dict]], output_path: str):
        """
        Save search results to a file.
        
        Args:
            results: Dictionary of search results
            output_path: Path to save the results
        """
        # Separate found and not found
        found = {k: v for k, v in results.items() if v is not None}
        not_found = [k for k, v in results.items() if v is None]
        
        output = {
            "summary": {
                "total_searched": len(results),
                "found": len(found),
                "not_found": len(not_found)
            },
            "found_nodes": found,
            "not_found_nodes": not_found
        }
        
        if output_path.endswith('.json'):
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(output, f, indent=2, ensure_ascii=False)
        else:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write("=" * 80 + "\n")
                f.write("COMFYUI NODE GITHUB SEARCH RESULTS\n")
                f.write("=" * 80 + "\n\n")
                
                f.write(f"Total Searched: {output['summary']['total_searched']}\n")
                f.write(f"Found: {output['summary']['found']}\n")
                f.write(f"Not Found: {output['summary']['not_found']}\n\n")
                
                f.write("=" * 80 + "\n")
                f.write("FOUND NODES\n")
                f.write("=" * 80 + "\n\n")
                
                for class_name, info in sorted(found.items()):
                    f.write(f"Class: {class_name}\n")
                    f.write(f"  Repository: {info['repo_name']}\n")
                    f.write(f"  URL: {info['repo_url']}\n")
                    f.write(f"  Description: {info['description']}\n")
                    f.write(f"  Stars: {info['stars']}\n")
                    f.write(f"  File: {info['file_path']}\n")
                    f.write(f"  File URL: {info['file_url']}\n")
                    f.write("\n")
                
                if not_found:
                    f.write("=" * 80 + "\n")
                    f.write("NOT FOUND NODES\n")
                    f.write("=" * 80 + "\n\n")
                    for class_name in sorted(not_found):
                        f.write(f"  - {class_name}\n")
        
        print(f"\n💾 Results saved to: {output_path}")


def main():
    """Main function for command-line usage."""
    import sys
    import os
    
    print("ComfyUI Node GitHub Finder")
    print("=" * 50)
    
    # Get workflow image path
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
    else:
        image_path = input("\nEnter path to ComfyUI workflow image (PNG): ").strip().strip('"').strip("'")
    
    if not os.path.exists(image_path):
        print(f"Error: File not found: {image_path}")
        return
    
    # Parse workflow
    print(f"\n📄 Parsing workflow from: {image_path}")
    parser = WorkflowParser(image_path)
    
    try:
        nodes, io_map, connections, prompts, loras = parser.parse_all()
        print(f"✓ Found {len(nodes)} nodes")
        
        # Display ControlNet warning
        if parser.uses_controlnet:
            print(f"\n⚠️  CONTROLNET DETECTED - This workflow uses ControlNet nodes")
        
        # Display LoRAs
        if loras:
            print(f"\n🎨 LoRAs Used: {len(loras)}")
            for lora in loras:
                print(f"   - {lora['lora_name']} (Model: {lora['model_strength']}, CLIP: {lora['clip_strength']})")
        
        # Display detected prompts
        if prompts.get('positive') or prompts.get('negative'):
            print(f"\n📝 Detected Prompts:")
            if prompts.get('positive'):
                print(f"   Positive: {len(prompts['positive'])} prompt(s)")
                for prompt in prompts['positive']:
                    preview = prompt['text'][:60] + '...' if len(prompt['text']) > 60 else prompt['text']
                    print(f"      - {preview}")
            if prompts.get('negative'):
                print(f"   Negative: {len(prompts['negative'])} prompt(s)")
                for prompt in prompts['negative']:
                    preview = prompt['text'][:60] + '...' if len(prompt['text']) > 60 else prompt['text']
                    print(f"      - {preview}")
    except Exception as e:
        print(f"Error parsing workflow: {e}")
        return
    
    # Initialize token manager
    token_manager = TokenManager()
    
    # Scan ComfyUI installation (optional)
    scanner = ComfyUIScanner()
    if scanner.prompt_for_path(token_manager):
        scanner.scan_all()
    
    # Get GitHub token (from .env or prompt)
    github_token = token_manager.get_or_prompt_token()
    
    if not github_token:
        print("\n❌ Error: GitHub token is required. Exiting.")
        return
    
    # Search GitHub
    finder = GitHubNodeFinder(github_token)
    results = finder.search_all_nodes(nodes, scanner)
    
    # Print summary
    found_count = sum(1 for v in results.values() if v is not None)
    print(f"\n✓ Summary:")
    print(f"  Found: {found_count}/{len(results)} custom nodes")
    
    # Handle found repositories
    comfyui_path = scanner.comfyui_path if scanner else None
    finder.handle_found_repos(results, str(comfyui_path) if comfyui_path else None)
    
    # Save results
    output_path = input("\nSave results to (default: node_repos.json): ").strip() or "node_repos.json"
    finder.save_results(results, output_path)


if __name__ == "__main__":
    main()
