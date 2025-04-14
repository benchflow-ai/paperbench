import json
import os
import glob
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap
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
        elif "litellm" in agent_match.lower():
            display_name = "Gemini via LiteLLM"
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
    
    # 1. Bar chart of final scores
    plt.figure(figsize=(12, 8))
    labels = [m['display_name'] for m in model_data]
    scores = [m['final_score'] for m in model_data]
    
    # Create colormap
    colors = ["#ff0000", "#ffff66", "#00cc44"]  # Red to yellow to green
    custom_cmap = LinearSegmentedColormap.from_list("red_to_green", colors, N=256)
    bar_colors = [custom_cmap(score) for score in scores]
    
    bars = plt.bar(labels, scores, color=bar_colors)
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
    
    # 2. Grid of model trees with bar chart
    # Create a 2x3 grid (or adjust based on number of models)
    rows = 2
    cols = 3
    fig = plt.figure(figsize=(20, 15))
    grid = gridspec.GridSpec(rows, cols, figure=fig)
    
    # Add bar chart at the top spanning multiple columns
    ax_bar = fig.add_subplot(grid[0, :2])  # Top-left spanning 2 columns
    bars = ax_bar.bar(labels, scores, color=bar_colors)
    ax_bar.set_ylim(0, 1)
    ax_bar.set_title('Model Performance Comparison', fontsize=16)
    ax_bar.grid(axis='y', linestyle='--', alpha=0.7)
    for bar in bars:
        height = bar.get_height()
        ax_bar.text(bar.get_x() + bar.get_width()/2., height + 0.01,
                f'{height:.2f}', ha='center', va='bottom', fontsize=12)
    
    # Create a table to show final scores
    ax_table = fig.add_subplot(grid[0, 2])  # Top-right
    cell_text = [[m['display_name'], f"{m['final_score']:.2f}"] for m in model_data]
    ax_table.axis('tight')
    ax_table.axis('off')
    table = ax_table.table(cellText=cell_text, 
                          colLabels=['Model', 'Score'],
                          loc='center',
                          cellLoc='center')
    table.auto_set_font_size(False)
    table.set_fontsize(12)
    table.scale(1, 1.5)
    ax_table.set_title("Final Scores", fontsize=16)
    
    # Add model thumbnail images from the tree visualizations
    for i, model in enumerate(model_data):
        if i < (rows-1) * cols:  # Limit to available grid slots
            row_idx = 1 + i // cols
            col_idx = i % cols
            
            ax = fig.add_subplot(grid[row_idx, col_idx])
            
            # Get the visualization file for this model
            viz_file = output_dir / f"{model['model_name']}_{model['agent_type']}_tree.png"
            if viz_file.exists():
                img = plt.imread(viz_file)
                ax.imshow(img)
                ax.set_title(f"{model['display_name']} ({model['final_score']:.2f})", fontsize=14)
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
    
    # Set custom colors for rows based on scores
    cell_colors = []
    for model in model_data:
        score = model['final_score']
        color = custom_cmap(score)
        # Make a slightly lighter version for better readability
        lighter_color = [min(1.0, c * 1.3) for c in color[:3]] + [0.3]  # Last value is alpha
        cell_colors.append([lighter_color, lighter_color, lighter_color])
    
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