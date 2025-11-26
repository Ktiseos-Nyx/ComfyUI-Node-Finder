"""
Debug Node Names

Helper script to identify the actual class names vs display names in workflows.
"""

import json
from workflow_parser import WorkflowParser
from comfyui_scanner import ComfyUIScanner


def debug_workflow_nodes(image_path: str, comfyui_path: str = None):
    """
    Debug node names in a workflow.
    
    Args:
        image_path: Path to workflow image
        comfyui_path: Optional path to ComfyUI installation
    """
    # Parse workflow
    print(f"📄 Parsing workflow from: {image_path}")
    parser = WorkflowParser(image_path)
    nodes, io_map, connections, prompts, loras = parser.parse_all()
    
    print(f"\n✓ Found {len(nodes)} nodes\n")
    
    # Get unique class types
    class_types = {}
    for node_id, node_info in nodes.items():
        class_name = node_info['class_type']
        if class_name not in class_types:
            class_types[class_name] = []
        class_types[class_name].append(node_id)
    
    print("=" * 80)
    print("NODE CLASS NAMES IN WORKFLOW")
    print("=" * 80)
    
    for class_name in sorted(class_types.keys()):
        node_ids = class_types[class_name]
        print(f"\nClass: {class_name}")
        print(f"  Count: {len(node_ids)}")
        print(f"  Node IDs: {', '.join(node_ids)}")
    
    # If ComfyUI path provided, check against installation
    if comfyui_path:
        print("\n" + "=" * 80)
        print("CHECKING AGAINST LOCAL INSTALLATION")
        print("=" * 80)
        
        scanner = ComfyUIScanner(comfyui_path)
        scanner.scan_all()
        
        print("\n" + "=" * 80)
        print("NODE CLASSIFICATION")
        print("=" * 80)
        
        for class_name in sorted(class_types.keys()):
            classification = scanner.classify_node(class_name)
            repo = scanner.get_custom_node_repo(class_name) if classification == 'custom' else None
            
            status = {
                'builtin': '✓ Built-in',
                'custom': f'✓ Custom ({repo})',
                'unknown': '✗ Unknown'
            }[classification]
            
            print(f"\n{class_name}")
            print(f"  {status}")
        
        # Check for similar names in custom nodes
        print("\n" + "=" * 80)
        print("SEARCHING FOR SIMILAR NAMES IN CUSTOM NODES")
        print("=" * 80)
        
        for class_name in sorted(class_types.keys()):
            if scanner.classify_node(class_name) == 'unknown':
                print(f"\n❓ {class_name}")
                
                # Search for partial matches
                matches = []
                search_lower = class_name.lower()
                
                for custom_name, repo in scanner.custom_nodes.items():
                    custom_lower = custom_name.lower()
                    
                    # Check for partial matches
                    if (search_lower in custom_lower or 
                        custom_lower in search_lower or
                        any(word in custom_lower for word in search_lower.split())):
                        matches.append((custom_name, repo))
                
                if matches:
                    print("  Possible matches:")
                    for match_name, match_repo in matches[:5]:  # Show top 5
                        print(f"    - {match_name} ({match_repo})")
                else:
                    print("  No similar names found in custom nodes")


def main():
    """Main function."""
    import sys
    
    print("Node Name Debugger")
    print("=" * 80)
    
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
    else:
        image_path = input("\nEnter path to workflow image: ").strip().strip('"').strip("'")
    
    comfyui_path = None
    if len(sys.argv) > 2:
        comfyui_path = sys.argv[2]
    else:
        check_local = input("\nCheck against local ComfyUI installation? (y/n) [y]: ").strip().lower() or 'y'
        if check_local == 'y':
            comfyui_path = input("Enter ComfyUI installation path: ").strip().strip('"').strip("'")
    
    debug_workflow_nodes(image_path, comfyui_path)


if __name__ == "__main__":
    main()
