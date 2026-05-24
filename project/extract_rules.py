import pickle
import numpy as np

# Load the model and scaler
with open('models/model.pkl', 'rb') as f:
    clf = pickle.load(f)
with open('models/scaler.pkl', 'rb') as f:
    scaler = pickle.load(f)

feature_names = ['Traffic Volume (Mbps)', 'Network Latency (ms)', 'Throughput (Mbps)', 'Packet Loss (%)', 'Signal Strength (dBm)', 'Resource Allocation (%)', 'Handover Success (0/1)']

tree = clf.tree_

def print_tree(node_id, depth):
    if depth >= 3: # depth 3 means 0, 1, 2
        return
    
    threshold_scaled = tree.threshold[node_id]
    feature_idx = tree.feature[node_id]
    
    if feature_idx != -2:  # Not a leaf
        feature_name = feature_names[feature_idx]
        # Invert scaling
        threshold_original = threshold_scaled * scaler.scale_[feature_idx] + scaler.mean_[feature_idx]
        
        indent = "  " * depth
        print(f"{indent}if {feature_name} <= {threshold_original:.4f}:")
        print_tree(tree.children_left[node_id], depth + 1)
        print(f"{indent}else:  # {feature_name} > {threshold_original:.4f}")
        print_tree(tree.children_right[node_id], depth + 1)

print("Decision Tree Rules (Depth 3):")
print_tree(0, 0)

# Print root rule specifically as requested
root_feature_idx = tree.feature[0]
root_threshold_scaled = tree.threshold[0]
root_feature_name = feature_names[root_feature_idx]
root_threshold_original = root_threshold_scaled * scaler.scale_[root_feature_idx] + scaler.mean_[root_feature_idx]
print(f"\nRoot rule: if {root_feature_name} <= {root_threshold_original:.4f}")
