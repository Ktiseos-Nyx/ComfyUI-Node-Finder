#!/usr/bin/env python3
"""
ComfyUI Workflow Analyzer - Master Script

This is the main entry point for analyzing ComfyUI workflow images.
It combines workflow parsing, node classification, and GitHub repository search
into a single interactive experience.

Usage:
    python comfyui_workflow_analyzer.py [image_path]
"""

import os
import sys
import time
from pathlib import Path
from typing import Dict, Optional

from workflow_parser import WorkflowParser
from comfyui_scanner import ComfyUIScanner
from github_node_finder import GitHubNodeFinder
from token_manager import TokenManager


def get_image_path() -> Optional[str]:
    """Prompt user for workflow image path."""
    if len(sys.argv) > 1:
        return sys.argv[1]
    
    path = input("\nEnter path to ComfyUI workflow image (PNG): ").strip().strip('"').strip("'")
    
    if not path:
        return None
    
    if not os.path.exists(path):
        print(f"❌ Error: File not found: {path}")
        return None
    
    return path


def get_output_format() -> tuple:
    """Prompt user for output format."""
    print("\nOutput options:")
    print("  1. JSON format (default: workflow_analysis.json)")
    print("  2. Text format (default: workflow_analysis.txt)")
    print("  3. Both formats")
    
    choice = input("Choose format (1/2/3) [1]: ").strip() or "1"
    
    if choice == "1":
        path = input("Output path [workflow_analysis.json]: ").strip() or "workflow_analysis.json"
        return [(path, "json")]
    elif choice == "2":
        path = input("Output path [workflow_analysis.txt]: ").strip() or "workflow_analysis.txt"
        return [(path, "txt")]
    elif choice == "3":
        json_path = input("JSON output path [workflow_analysis.json]: ").strip() or "workflow_analysis.json"
        txt_path = input("Text output path [workflow_analysis.txt]: ").strip() or "workflow_analysis.txt"
        return [(json_path, "json"), (txt_path, "txt")]
    else:
        return [("workflow_analysis.json", "json")]


def display_workflow_summary(parser: WorkflowParser, nodes: Dict, prompts: Dict, loras: list):
    """Display a summary of the parsed workflow."""
    print("\n" + "=" * 80)
    print("WORKFLOW SUMMARY")
    print("=" * 80)
    
    print(f"\n📊 Statistics:")
    print(f"   Total Nodes: {len(nodes)}")
    print(f"   Positive Prompts: {len(prompts.get('positive', []))}")
    print(f"   Negative Prompts: {len(prompts.get('negative', []))}")
    print(f"   LoRAs Used: {len(loras)}")
    
    # ControlNet warning
    if parser.uses_controlnet:
        print(f"\n⚠️  CONTROLNET DETECTED")
        print(f"   This workflow uses ControlNet nodes. Make sure you have:")
        print(f"   - ControlNet models installed")
        print(f"   - Compatible ControlNet custom nodes")
    
    # AI Prompt Enhancement warning
    if parser.uses_ai_prompt_enhancement:
        print(f"\n🤖 AI PROMPT ENHANCEMENT DETECTED")
        print(f"   The displayed prompts may have been modified by AI:")
        for enhancer in parser.ai_prompt_enhancers:
            print(f"   - {enhancer['class_type']} (Node {enhancer['node_id']})")
    
    # Display LoRAs
    if loras:
        print(f"\n🎨 LoRAs:")
        for i, lora in enumerate(loras, 1):
            print(f"   [{i}] {lora['lora_name']}")
            print(f"       Model: {lora['model_strength']}, CLIP: {lora['clip_strength']}")
    
    # Display prompts (preview)
    if prompts.get('positive'):
        print(f"\n📝 Positive Prompt Preview:")
        for prompt in prompts['positive'][:1]:  # Show first one
            preview = prompt['text'][:100] + '...' if len(prompt['text']) > 100 else prompt['text']
            print(f"   {preview}")
    
    if prompts.get('negative'):
        print(f"\n🚫 Negative Prompt Preview:")
        for prompt in prompts['negative'][:1]:  # Show first one
            preview = prompt['text'][:100] + '...' if len(prompt['text']) > 100 else prompt['text']
            print(f"   {preview}")


def analyze_nodes(nodes: Dict, scanner: ComfyUIScanner) -> Dict[str, str]:
    """
    Analyze and classify all nodes in the workflow.
    
    Returns:
        Dictionary mapping node class names to their classification
    """
    print("\n" + "=" * 80)
    print("NODE ANALYSIS")
    print("=" * 80)
    
    # Get unique node types
    unique_nodes = {}
    for node_info in nodes.values():
        class_name = node_info['class_type']
        if class_name not in unique_nodes:
            unique_nodes[class_name] = scanner.classify_node(class_name)
    
    # Count by classification
    builtin_count = sum(1 for c in unique_nodes.values() if c == 'builtin')
    custom_count = sum(1 for c in unique_nodes.values() if c == 'custom')
    unknown_count = sum(1 for c in unique_nodes.values() if c == 'unknown')
    
    print(f"\n📦 Node Classification:")
    print(f"   Built-in: {builtin_count}")
    print(f"   Custom (installed): {custom_count}")
    print(f"   Unknown (not installed): {unknown_count}")
    
    if unknown_count > 0:
        print(f"\n⚠️  Found {unknown_count} unknown node(s) - you may need to install additional custom nodes")
    
    return unique_nodes


def deep_dive_nodes(nodes: Dict, unique_nodes: Dict[str, str], scanner: ComfyUIScanner, 
                   comfyui_path: Optional[str], token_mgr: TokenManager):
    """Perform deep dive analysis and offer to download missing nodes."""
    print("\n" + "=" * 80)
    print("DEEP DIVE - NODE DETAILS")
    print("=" * 80)
    
    # List all nodes by classification
    builtin_nodes = [name for name, cls in unique_nodes.items() if cls == 'builtin']
    custom_nodes = [name for name, cls in unique_nodes.items() if cls == 'custom']
    unknown_nodes = [name for name, cls in unique_nodes.items() if cls == 'unknown']
    
    if builtin_nodes:
        print(f"\n✅ Built-in Nodes ({len(builtin_nodes)}):")
        for node in sorted(builtin_nodes):
            print(f"   - {node}")
    
    if custom_nodes:
        print(f"\n🔧 Custom Nodes - Already Installed ({len(custom_nodes)}):")
        for node in sorted(custom_nodes):
            repo = scanner.custom_nodes.get(node, 'unknown')
            print(f"   - {node} (from: {repo})")
    
    if unknown_nodes:
        print(f"\n❓ Unknown Nodes - Not Installed ({len(unknown_nodes)}):")
        for node in sorted(unknown_nodes):
            print(f"   - {node}")
        
        # Offer to search GitHub
        search = input(f"\n🔍 Search GitHub for missing nodes? (y/n) [y]: ").strip().lower() or 'y'
        
        if search == 'y':
            # Get or prompt for GitHub token
            github_token = token_mgr.get_or_prompt_token(auto_use=True)
            
            if not github_token:
                print("\n⚠️  No GitHub token provided. Cannot search GitHub.")
                return
            
            # Initialize finder
            finder = GitHubNodeFinder(github_token=github_token)
            
            # Search for unknown nodes
            print(f"\n🔍 Searching GitHub for {len(unknown_nodes)} node(s)...")
            print(f"   (Adding delays to avoid rate limiting...)")
            results = {}
            for i, node_name in enumerate(unknown_nodes, 1):
                result = finder.search_node_class(node_name)
                results[node_name] = result
                
                if result:
                    print(f"   [{i}/{len(unknown_nodes)}] ✓ Found: {node_name} -> {result['repo_name']}")
                else:
                    print(f"   [{i}/{len(unknown_nodes)}] ✗ Not found: {node_name}")
                
                # Add delay between requests to avoid rate limiting (except for last one)
                if i < len(unknown_nodes):
                    time.sleep(2)  # 2 second delay between searches
            
            # Handle found repositories
            if any(results.values()):
                finder.handle_found_repos(results, comfyui_path)


def main():
    """Main entry point for the workflow analyzer."""
    print("=" * 80)
    print("ComfyUI Workflow Analyzer")
    print("=" * 80)
    
    # Get image path
    image_path = get_image_path()
    if not image_path:
        print("❌ No image path provided. Exiting.")
        return
    
    # Load configuration using TokenManager
    token_mgr = TokenManager()
    comfyui_path = token_mgr.get_or_prompt_comfyui_location(auto_use=True)
    github_token = token_mgr.load_token()  # Load but don't prompt yet
    
    # Initialize scanner if ComfyUI path is available
    scanner = None
    if comfyui_path:
        print(f"\n📁 ComfyUI Location: {comfyui_path}")
        scanner = ComfyUIScanner(comfyui_path)
        scanner.scan_all()
    else:
        print("\n⚠️  Skipping node classification (no ComfyUI path provided)")
    
    # Parse workflow
    print(f"\n📄 Parsing workflow from: {image_path}")
    parser = WorkflowParser(image_path)
    
    try:
        nodes, io_map, connections, prompts, loras = parser.parse_all()
        print(f"✓ Parsing complete!")
    except Exception as e:
        print(f"❌ Error parsing workflow: {e}")
        return
    
    # Get output format and save
    outputs = get_output_format()
    for output_path, format_type in outputs:
        parser.save_to_file(output_path, format=format_type)
        print(f"✓ Data saved to: {output_path}")
    
    # Display summary
    display_workflow_summary(parser, nodes, prompts, loras)
    
    # Analyze nodes if scanner is available
    if scanner:
        unique_nodes = analyze_nodes(nodes, scanner)
        
        # Offer deep dive
        deep_dive = input(f"\n🔬 Perform deep dive into nodes? (y/n) [n]: ").strip().lower()
        
        if deep_dive == 'y':
            deep_dive_nodes(nodes, unique_nodes, scanner, comfyui_path, token_mgr)
    else:
        print("\n⚠️  Skipping node analysis (ComfyUI path not provided)")
    
    print("\n" + "=" * 80)
    print("✅ Analysis Complete!")
    print("=" * 80)


if __name__ == "__main__":
    main()
