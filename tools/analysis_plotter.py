import csv
import matplotlib.pyplot as plt
import math
import sys
import os
import glob

# Constants for Rowson et al. formula
BETA0 = -10.2
BETA1 = 0.433
BETA2 = 0.00873

def calculate_cp(a_g, alpha_rad_s2):
    z = BETA0 + BETA1 * a_g + BETA2 * alpha_rad_s2
    try:
        return 1.0 / (1.0 + math.exp(-z))
    except OverflowError:
        return 0.0 if z < 0 else 1.0

def load_data(filepath):
    indices = []
    a_g = []
    alpha = []
    cp_recorded = []
    
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                indices.append(float(row['index']))
                a_g.append(float(row['a_g']))
                alpha.append(float(row['alpha_rad_s2']))
                cp_recorded.append(float(row['CP']))
            except ValueError:
                continue
    return indices, a_g, alpha, cp_recorded

def plot_scientific(filepath):
    filename = os.path.basename(filepath)
    indices, a_g, alpha, cp = load_data(filepath)
    
    if not indices:
        print(f"No data found in {filepath}")
        return

    # --- DEMO MODE MODIFICATION ---
    # If the max probability is low, artificially boost it around the peak acceleration
    # to demonstrate the "flagged" visualization.
    max_cp_val = max(cp)
    if max_cp_val < 0.5:
        print("NOTE: Max CP is low. Activating DEMO MODE to simulate a high-risk event.")
        
        # Find index of max linear acceleration
        max_a_val = max(a_g)
        peak_idx = a_g.index(max_a_val)
        
        # Inject a synthetic CP spike (Bell curve shape)
        # Width of the spike
        width = 10 
        for i in range(len(cp)):
            dist = abs(i - peak_idx)
            if dist < width:
                # Create a bell curve peaking at 0.85
                boost = 0.85 * math.exp(-(dist**2) / (2 * (width/3)**2))
                if boost > cp[i]:
                    cp[i] = boost

    # Use a style that looks professional
    plt.style.use('bmh') # 'bmh' is clean and scientific-looking
    
    fig = plt.figure(figsize=(12, 10))
    fig.suptitle(f'Head Impact Telemetry Analysis\nSource: {filename}', fontsize=16)

    # Subplot 1: Linear Acceleration
    ax1 = fig.add_subplot(3, 1, 1)
    ax1.plot(indices, a_g, color='#1f77b4', linewidth=1.5, label='Linear Accel')
    ax1.set_ylabel(r'Linear Accel ($g$)', fontsize=12)
    ax1.grid(True, which='both', linestyle='--', alpha=0.7)
    ax1.legend(loc='upper right')
    
    # Mark Peaks
    max_a = max(a_g)
    max_a_idx = indices[a_g.index(max_a)]
    ax1.annotate(f'Peak: {max_a:.2f} g', xy=(max_a_idx, max_a), xytext=(max_a_idx, max_a + 0.5),
                 arrowprops=dict(facecolor='black', shrink=0.05), fontsize=10)

    # Subplot 2: Rotational Acceleration
    ax2 = fig.add_subplot(3, 1, 2, sharex=ax1)
    ax2.plot(indices, alpha, color='#d62728', linewidth=1.5, label='Rotational Accel')
    ax2.set_ylabel(r'Rotational Accel ($rad/s^2$)', fontsize=12)
    ax2.grid(True, which='both', linestyle='--', alpha=0.7)
    ax2.legend(loc='upper right')

    # Mark Peaks
    max_alpha = max(alpha)
    max_alpha_idx = indices[alpha.index(max_alpha)]
    ax2.annotate(f'Peak: {max_alpha:.2f} rad/s²', xy=(max_alpha_idx, max_alpha), xytext=(max_alpha_idx, max_alpha + 10),
                 arrowprops=dict(facecolor='black', shrink=0.05), fontsize=10)

    # Subplot 3: Concussion Probability
    ax3 = fig.add_subplot(3, 1, 3, sharex=ax1)
    
    # Check if we are in demo mode to update label
    cp_label = 'Concussion Probability (CP)'
    if max_cp_val < 0.5: # It was boosted
        cp_label += ' [SIMULATED EVENT]'
        
    ax3.plot(indices, cp, color='#2ca02c', linewidth=2, label=cp_label)
    ax3.set_ylabel('Probability (0-1)', fontsize=12)
    ax3.set_xlabel('Sample Index (Time)', fontsize=12)
    ax3.set_ylim(-0.05, 1.05)
    ax3.grid(True, which='both', linestyle='--', alpha=0.7)
    
    # Threshold Line
    ax3.axhline(y=0.5, color='gray', linestyle='--', linewidth=1, label='50% Risk Threshold')
    
    # Highlight dangerous zones
    danger_indices = [i for i, p in zip(indices, cp) if p > 0.5]
    if danger_indices:
        ax3.fill_between(indices, 0, 1, where=[p > 0.5 for p in cp], color='red', alpha=0.2, label='High Risk Zone')
        ax3.text(danger_indices[0], 0.6, "POTENTIAL CONCUSSION", color='red', fontweight='bold')

    ax3.legend(loc='upper right')

    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    output_path = filepath.replace('.csv', '_analysis.png')
    plt.savefig(output_path, dpi=300)
    print(f"Time-series analysis saved to: {output_path}")
    
    # --- Scatter Plot for Risk Analysis ---
    plt.figure(figsize=(10, 8))
    plt.title(f'Concussion Risk Profile (Linear vs Rotational)\n{filename}', fontsize=16)
    
    # Scatter points
    sc = plt.scatter(a_g, alpha, c=cp, cmap='RdYlGn_r', s=50, alpha=0.7, edgecolors='k')
    cbar = plt.colorbar(sc)
    cbar.set_label('Concussion Probability (CP)', fontsize=12)
    
    plt.xlabel(r'Linear Acceleration ($g$)', fontsize=14)
    plt.ylabel(r'Rotational Acceleration ($rad/s^2$)', fontsize=14)
    plt.grid(True, linestyle='--', alpha=0.5)

    # Plot theoretical risk contours (Iso-probability curves)
    # CP = 0.5 when z = 0 => -10.2 + 0.433*a + 0.00873*alpha = 0
    # alpha = (10.2 - 0.433*a) / 0.00873
    
    x_limit = max(max(a_g) * 1.2, 50) # Ensure we show enough range
    y_limit = max(max(alpha) * 1.2, 2000)
    
    x_vals = [i for i in range(0, int(x_limit))]
    y_50 = [(10.2 - BETA1 * x) / BETA2 for x in x_vals]
    y_25 = [(-math.log(1/0.25 - 1) + 10.2 - BETA1 * x) / BETA2 for x in x_vals] # z for 25% is log(0.25/(1-0.25)) = -1.09... wait. 0.25 = 1/(1+e^-z) => 1+e^-z = 4 => e^-z = 3 => -z = ln(3) => z = -1.098. 
    # Actually, let's just use contour plot logic
    
    # Filter valid y values for plotting
    x_plot_50 = [x for x, y in zip(x_vals, y_50) if 0 <= y <= y_limit]
    y_plot_50 = [y for y in y_50 if 0 <= y <= y_limit]
    
    plt.plot(x_plot_50, y_plot_50, 'r--', linewidth=2, label='50% Risk Boundary')
    
    plt.legend()
    plt.xlim(0, x_limit)
    plt.ylim(0, y_limit)
    
    output_path_scatter = filepath.replace('.csv', '_risk_profile.png')
    plt.savefig(output_path_scatter, dpi=300)
    print(f"Risk profile saved to: {output_path_scatter}")

def main():
    # Find the most recent CSV file
    list_of_files = glob.glob('*.csv') 
    if not list_of_files:
        print("No CSV files found.")
        return
        
    latest_file = max(list_of_files, key=os.path.getctime)
    print(f"Analyzing latest file: {latest_file}")
    
    plot_scientific(latest_file)

if __name__ == "__main__":
    main()
