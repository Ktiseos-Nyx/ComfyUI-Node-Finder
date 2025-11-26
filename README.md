# ComfyUI-Node-Finder

Analyze ComfyUI workflow images to identify missing custom nodes and automatically find their GitHub repositories.

## Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the application:**
   ```bash
   python app.py
   ```

3. **Follow the prompts:**
   - Provide your GitHub token (required - see [GitHub Token](#github-token-required) section)
   - Specify your ComfyUI installation path
   - Select a workflow PNG image to analyze

The tool will:
- Extract workflow metadata (nodes, prompts, LoRAs)
- Identify missing custom nodes
- Search for repositories using Comfy Registry and GitHub
- Offer to download missing nodes directly to your `custom_nodes` folder

## Features

- 🔍 **Workflow Analysis** - Extract prompts, LoRAs, and node information from PNG images
- 🎯 **Smart Node Detection** - Identifies built-in, installed, and missing custom nodes
- 📦 **Automatic Repository Discovery** - Searches Comfy Registry and GitHub for missing nodes
- ⚡ **Intelligent Caching** - Caches scan results and registry data to avoid redundant work
- 🚀 **One-Click Installation** - Clone repositories directly to your ComfyUI installation
- 🔄 **Conditioning Chain Tracing** - Accurately extracts prompts from complex conditioning workflows
- 🚫 **Disabled Node Filtering** - Ignores muted/disabled nodes when extracting prompts

## Workflow Parser

Parse ComfyUI workflow metadata from PNG images and extract structured data about nodes, inputs/outputs, and connections.

### Command Line Usage

```bash
# Parse workflow and save to JSON
python workflow_parser.py workflow_image.png output.json

# Parse workflow and save to text file
python workflow_parser.py workflow_image.png output.txt
```

#### Programmatic Usage

```python
from workflow_parser import WorkflowParser

# Initialize parser
parser = WorkflowParser("path/to/workflow_image.png")

# Parse all data at once
nodes, io_map, connections = parser.parse_all()

# Save to file
parser.save_to_file("analysis.json", format="json")  # JSON format
parser.save_to_file("analysis.txt", format="txt")    # Text format

# Access individual dictionaries
print(f"Nodes: {len(nodes)}")
print(f"Connections: {len(connections)}")
```

### Output Structure

The parser generates three dictionaries:

1. **Nodes Dictionary**: Core node properties (type, position, size, widgets)
2. **I/O Map Dictionary**: Input and output definitions for each node
3. **Connections Dictionary**: How nodes are connected to each other

See `example_usage.py` for more detailed examples.

## GitHub Node Finder

Search GitHub for ComfyUI custom node repositories based on node class names found in workflows.

### Usage

#### Command Line

```bash
# Search for all custom nodes in a workflow
python github_node_finder.py workflow_image.png

# Or run interactively
python github_node_finder.py
```

#### Programmatic Usage

```python
from workflow_parser import WorkflowParser
from github_node_finder import GitHubNodeFinder

# Parse workflow
parser = WorkflowParser("workflow.png")
nodes, io_map, connections = parser.parse_all()

# Search GitHub for custom nodes
finder = GitHubNodeFinder(github_token="optional_token")
results = finder.search_all_nodes(nodes)

# Save results
finder.save_results(results, "node_repos.json")
```

### Node Search Features

- **Comfy Registry Integration** - Downloads and caches the entire Comfy Registry for fast lookups
- **Local ComfyUI scanning** - Identifies built-in and already-installed custom nodes
- **Smart filtering** - Only searches for unknown nodes not in registry or local installation
- **Automatic classification** - Separates built-in, custom, and unknown nodes
- **Interactive installation** - Download repos directly to custom_nodes or open in browser
- **Git integration** - Clone repositories with one command
- **Rate limit handling** with GitHub token support
- **Persistent caching** - Caches scan results and registry data to avoid redundant work
- **Change detection** - Only rescans custom_nodes directory when changes are detected
- **Multiple search strategies** for better results
- **JSON and text output** formats

### GitHub Token (REQUIRED)

⚠️ **GitHub's code search API requires authentication.**

**How to create a token:**
1. Go to: https://github.com/settings/tokens
2. Click "Generate new token" → "Generate new token (classic)"
3. Give it a name (e.g., "ComfyUI Node Finder")
4. Select scopes: **`public_repo`** (or `repo` for private repos)
5. Click "Generate token"
6. Copy the token (you won't see it again!)

**Token Storage:**
- The tool will automatically save your token to a `.env` file
- `.env` is git-ignored for security
- You only need to enter your token once
- Manage tokens with: `python token_manager.py [save|load|delete|check]`

**ComfyUI Location Storage:**
- Optionally save your ComfyUI installation path to `.env`
- Add `COMFYUI_LOCATION=D:\StableDiffusion\ComfyUI` to your `.env` file
- The tool will remember your installation path for future scans

**Rate limits:**
- With token: 5,000 requests/hour
- Token is required for code search API

### Interactive Installation

After finding repositories, the tool will offer to:
1. **Download repositories** - Clone directly to your `custom_nodes` folder using git
2. **Open in browser** - Open all found repositories in your default browser

**Requirements for downloading:**
- Git must be installed: https://git-scm.com/
- ComfyUI location must be configured in `.env`

See `example_github_search.py` for more examples.
