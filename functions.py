import numpy as np
import pandas as pd
import statsmodels.api as sm
import seaborn as sns
import matplotlib.pyplot as plt
import yaml
from datetime import datetime, timedelta
import os


with open('conf.yaml', 'r') as conf_file:
    conf = yaml.safe_load(conf_file)

days_number = conf["params"]["days_number"]
starting_date = conf["params"]["starting_date"]
max_batches_per_day = conf["params"]["max_batches_per_day"]
sc_quantity = conf["params"]["sc_quantity"]
sc_size_avg = conf["params"]["sc_size_avg"]
sc_size_sd = conf["params"]["sc_size_sd"]
target_sc_rpc_pool_size = conf["params"]["target_sc_rpc_pool_size"]
sc_shrinkage_rate_avg = conf["params"]["sc_shrinkage_rate_avg"]
sc_shrinkage_rate_sd = conf["params"]["sc_shrinkage_rate_sd"]
general_shrinkage_rate_avg = conf["params"]["general_shrinkage_rate_avg"]
general_shrinkage_rate_sd = conf["params"]["general_shrinkage_rate_sd"]
rpc_batch_avg_size = conf["params"]["rpc_batch_avg_size"]
rpc_batch_sd_size = conf["params"]["rpc_batch_sd_size"]
rpc_trip_avg_days_duration = conf["params"]["rpc_trip_avg_days_duration"]
rpc_trip_sd_days_duration = conf["params"]["rpc_trip_sd_days_duration"]


def simulate_data():

    start_date = datetime.strptime(starting_date, "%Y-%m-%d")
    end_date = start_date + timedelta(days=days_number)

    #Initialize storage center sizes and shrinkage rates
    storage_centers = {
        sc_id: {
            "size": max(1, int(np.random.normal(sc_size_avg, sc_size_sd))),
            "shrinkage_rate": min(1, max(0, np.random.normal(sc_shrinkage_rate_avg, sc_shrinkage_rate_sd)))
        }
        for sc_id in range(1, sc_quantity + 1)
    }

    for sc_id in range(1, sc_quantity + 1):
        storage_centers[sc_id]["available_boxes"] = storage_centers[sc_id]["size"]

    #List to hold simulated rows
    data = []

    for day in range(days_number):
        current_date = start_date + timedelta(days=day)

        for sc_id, sc_data in storage_centers.items():
            #Check if storage center has the minimun available rpcs
            if sc_data["available_boxes"] < target_sc_rpc_pool_size:
                continue

            #Determine the number of batches for storage center this day
            num_batches = np.random.randint(1, max_batches_per_day + 1)

            for _ in range(num_batches):
                batch_size = max(1, int(np.random.normal(rpc_batch_avg_size, rpc_batch_sd_size)))

                #Check if batch size doesn't exceed available rpcs
                if batch_size > sc_data["available_boxes"]:
                    continue

                #Generate rental and return dates
                rental_date = current_date
                trip_duration = max(1, int(np.random.normal(rpc_trip_avg_days_duration, rpc_trip_sd_days_duration)))
                return_date = rental_date + timedelta(days=trip_duration)

                #Calculate the shrinkage rate for this batch
                batch_specific_shrinkage = max(0, np.random.normal(general_shrinkage_rate_avg, general_shrinkage_rate_sd))
                total_shrinkage_rate = min(1, sc_data["shrinkage_rate"] + batch_specific_shrinkage)

                #Generate lost rpc quantity
                lost_boxes_quantity = min(batch_size, int(batch_size * total_shrinkage_rate))

                #Update available rpcs in the storage center
                sc_data["available_boxes"] -= batch_size

                #Schedule return of boxes (excluding lost ones)
                return_boxes = batch_size - lost_boxes_quantity
                data.append([
                    sc_id,
                    batch_size,
                    rental_date,
                    return_date,
                    lost_boxes_quantity,
                    sc_data["available_boxes"]
                ])

                #Add return event to replenish available rpc
                storage_centers[sc_id]["return_date"] = storage_centers[sc_id].get("return_date", [])
                storage_centers[sc_id]["return_date"].append((return_date, return_boxes))

        #Process returns for the current day
        for sc_id, sc_data in storage_centers.items():
            if "return_date" in sc_data:
                returns_today = [entry for entry in sc_data["return_date"] if entry[0] == current_date]
                for _, return_boxes in returns_today:
                    sc_data["available_boxes"] += return_boxes
                sc_data["return_date"] = [entry for entry in sc_data["return_date"] if entry[0] > current_date]

    #Create the DataFrame
    columns = ["storage_center", "batch_size", "rental_date", "return_date", "lost_boxes_quantity", "pool_size"]
    df = pd.DataFrame(data, columns=columns)

    #Drop not returned batches
    df = df[df.return_date < end_date]

    return df

def get_shrinkage_rates(df):
    df['shrinkage_rate'] = df['lost_boxes_quantity'] / df['batch_size']
    return df

def plot_shrinkage_rates_by_sc(dataframe, output_dir):
    os.makedirs(output_dir, exist_ok=True)

    #Iterate through each storage center
    for storage_center in dataframe['storage_center'].unique():
        sc_data = dataframe[dataframe['storage_center'] == storage_center]

        #Plot the histogram
        plt.figure(figsize=(10, 6))
        sns.histplot(sc_data['shrinkage_rate'], bins=30, kde=True, color='blue')
        plt.title(f'Distribution of Shrinkage Rates for Storage Center {storage_center}', fontsize=16)
        plt.xlabel('Shrinkage Rate', fontsize=14)
        plt.ylabel('Frequency', fontsize=14)
        plt.grid(axis='y', linestyle='--', alpha=0.7)

        #Save the plot to the output directory
        file_path = os.path.join(output_dir, f"shrinkage_rate_sc_{storage_center}.png")
        plt.savefig(file_path)
        plt.close()

def plot_shrinkage_rate(dataframe, output_dir):
    os.makedirs(output_dir, exist_ok=True)

    plt.figure(figsize=(10, 6))
    sns.histplot(dataframe['shrinkage_rate'], bins=30, kde=True, color='blue')
    plt.title('Distribution of overall Shrinkage Rates', fontsize=16)
    plt.xlabel('Shrinkage Rate', fontsize=14)
    plt.ylabel('Frequency', fontsize=14)
    plt.grid(axis='y', linestyle='--', alpha=0.7)

    #Save plot to the output directory
    file_path = os.path.join(output_dir, f"shrinkage_rate_overall.png")
    plt.savefig(file_path)
    plt.close()

def plot_pool_size(dataframe, output_dir):
    os.makedirs(output_dir, exist_ok=True)

    #Create plot
    plt.figure(figsize=(12, 8))
    sns.lineplot(
        data=dataframe,
        x="rental_date",
        y="pool_size",
        hue="storage_center",
        palette="tab10"
    )
    plt.title("Pool Size Over Time by Storage Center", fontsize=16)
    plt.xlabel("Rental Date", fontsize=14)
    plt.ylabel("Pool Size", fontsize=14)
    plt.legend(title="Storage Center", fontsize=12, title_fontsize=13)
    plt.grid(axis='y', linestyle='--', alpha=0.7)

    #Save plot to the output directory
    file_path = os.path.join(output_dir, f"pool_size.png")
    plt.savefig(file_path)
    plt.close()