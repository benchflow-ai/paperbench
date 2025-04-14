import json
import os
import glob
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
import matplotlib.gridspec as gridspec

# Base directory
base_dir = Path("/Users/hongjixu/Documents/repos/paperbench/project/paperbench/runs")
output_dir = base_dir / "images"

# Create output directory if it doesn't exist
os.makedirs(output_dir, exist_ok=True)

# Find all pb_result.json files in the runs directory and its subdirectories
result_files = list(base_dir.glob("**/*pb_result.json"))
print(f"Found {len(result_files)} result files")

# Extract model data and scores
model_data = []

for file_path in result_files:
    try:
        # Extract meaningful identifiers from the path
        model_name = file_path.parent.name.split('_')[0]  # e.g., "rice"
        
        # Get the agent type from grandparent directory 
        agent_match = ""
        parent_parts = file_path.parent.parent.name.split('_')
        for part in parent_parts:
            if any(x in part.lower() for x in ["agent", "gemini", "gpt", "claude"]):
                agent_match = part
                break
                
        # Fall back to a substring if needed
        if not agent_match and len(parent_parts) > 3:
            agent_match = parent_parts[3]
        
        # Load JSON data
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Get the final score (root task score)
        root_task = data["paperbench_result"]["judge_output"]["graded_task_tree"]
        final_score = root_task.get("score", 0)
        
        # Get model display name
        if "anthropic" in agent_match.lower():
            display_name = "Claude 3.7"
        elif "openai" in agent_match.lower():
            display_name = "GPT-4"
        elif "llama" in agent_match.lower():
            display_name = "Llama 4"
        elif "litellm" in agent_match.lower() or "gemini" in agent_match.lower():
            display_name = "Gemini 2.5 pro"
        else:
            display_name = agent_match
        
        # Store relevant data
        model_info = {
            'agent_type': agent_match,
            'display_name': display_name,
            'final_score': final_score,
            'file_path': file_path,
            'model_name': model_name
        }
        
        # Extract subtask scores if available
        if "sub_tasks" in root_task:
            for i, subtask in enumerate(root_task.get("sub_tasks", [])):
                name = subtask.get("name", f"Subtask {i}")
                score = subtask.get("score", 0)
                model_info[name] = score
        
        model_data.append(model_info)
        print(f"Extracted data for {display_name}")
    
    except Exception as e:
        print(f"Error processing {file_path}: {e}")

# Create comparison visualizations
if model_data:
    # Sort by final score (descending)
    model_data.sort(key=lambda x: x['final_score'], reverse=True)
    
    # Use a single consistent colormap - Blues
    cmap = plt.colormaps['Blues']
    
    # Create consistent colors for each model (darker blue = higher score)
    model_colors = [cmap(0.4 + 0.6 * score) for score in [m['final_score'] for m in model_data]]
    
    # 1. Bar chart of final scores
    plt.figure(figsize=(12, 8))
    labels = [m['display_name'] for m in model_data]
    scores = [m['final_score'] for m in model_data]
    
    bars = plt.bar(labels, scores, color=model_colors)
    plt.ylim(0, 1)
    plt.xlabel('Model', fontsize=14)
    plt.ylabel('Final Score', fontsize=14)
    plt.title('Comparison of Final Scores Across Models', fontsize=18)
    plt.xticks(rotation=45, ha='right')
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    
    # Add score labels on top of bars
    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height + 0.01,
                f'{height:.2f}', ha='center', va='bottom', fontsize=12)
    
    plt.tight_layout()
    plt.savefig(output_dir / "score_comparison.png")
    plt.close()
    
    # 2. Grid of model trees - exactly 2x2
    fig = plt.figure(figsize=(20, 20))
    
    # Create a simple 2x2 grid
    gs = gridspec.GridSpec(2, 2, figure=fig)
    
    # Add model thumbnail images from the tree visualizations
    for i, model in enumerate(model_data):
        if i >= 4:  # Only show top 4 models
            break
            
        row_idx = i // 2
        col_idx = i % 2
        
        ax = fig.add_subplot(gs[row_idx, col_idx])
        
        # Get the visualization file for this model
        viz_file = output_dir / f"{model['model_name']}_{model['agent_type']}_tree.png"
        if viz_file.exists():
            img = plt.imread(viz_file)
            ax.imshow(img)
            ax.set_title(f"{model['display_name']} - Score: {model['final_score']:.2f}", fontsize=16)
        else:
            ax.text(0.5, 0.5, "Visualization not available", 
                   ha='center', va='center', fontsize=12)
        ax.axis('off')
    
    plt.tight_layout()
    plt.savefig(output_dir / "model_comparison_grid.png")
    plt.close()
    
    # 3. Create a focused visual comparison with just the scores and rankings
    plt.figure(figsize=(10, 8))
    
    # Set up the table data
    table_data = []
    for rank, model in enumerate(model_data, start=1):
        table_data.append([
            f"{rank}",
            model['display_name'],
            f"{model['final_score']:.2f}"
        ])
    
    # Create a table with no axes
    ax = plt.gca()
    ax.axis('tight')
    ax.axis('off')
    
    # Set consistent blue-themed colors for rows
    cell_colors = []
    for i, model in enumerate(model_data):
        color = cmap(0.3 + 0.7 * model['final_score'])  # Scale to use middle-to-high range of colormap
        # Add slight alpha for better readability
        adjusted_color = (*color[:3], 0.3)  # RGB with alpha 0.3
        row_color = [adjusted_color] * 3  # Apply to all cells in the row
        cell_colors.append(row_color)
    
    table = ax.table(cellText=table_data,
                    colLabels=["Rank", "Model", "Score"],
                    loc='center',
                    cellLoc='center',
                    cellColours=cell_colors)
    table.auto_set_font_size(False)
    table.set_fontsize(14)
    table.scale(1, 2)
    
    plt.title("Model Performance Ranking", fontsize=18, pad=20)
    plt.tight_layout()
    plt.savefig(output_dir / "results.png")
    plt.close()
    
    print(f"Generated comparison visualizations in {output_dir}")
else:
    print("No model data available for comparison") 