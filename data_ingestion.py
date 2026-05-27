import pandas as pd
import os
import yaml
import pymongo
from datetime import datetime

# Mapping of activity IDs to their corresponding labels based on PAMAP2 documentation
activities_dict = {
    1: 'lying',
    2: 'sitting',
    3: 'standing',
    4: 'walking',
    5: 'running',
    6: 'cycling',
    7: 'Nordic walking',
    9: 'watching TV',
    10: 'computer work',
    11: 'car driving',
    12: 'ascending stairs',
    13: 'descending stairs',
    16: 'vacuum cleaning',
    17: 'ironing',
    18: 'folding laundry',
    19: 'house cleaning',
    20: 'playing soccer',
    24: 'rope jumping'
}

def process_and_upload(folder_path, split_name, collection):
    for file in os.listdir(folder_path): 
        file_path = os.path.join(folder_path, file)

        # We only read the columns we need
        cols_to_use = [1, 4, 5, 6, 10, 11, 12, 22, 23, 24, 28, 29, 30, 39, 40, 41, 45, 46, 47]
        df = pd.read_csv(file_path, sep=" ", header=None, usecols=cols_to_use)

        # Filtering out rows where activity_id is 0 and dropping any rows with NaN values
        df = df[df[1] != 0].dropna()
        subject = file.replace("subject", "").replace(".dat", "")

        # Definition of sensor locations and their corresponding columns in PAMAP2
        locations = {
            "hand":  {'acc': [4, 5, 6], 'gyr': [10, 11, 12]},
            "chest": {'acc': [22, 23, 24], 'gyr': [28, 29, 30]},
            "ankle": {'acc': [39, 40, 41], 'gyr': [45, 46, 47]}
        }

        for loc, cols in locations.items():
            # Grouping by activity to create segments
            grouped = df.groupby(1) 
            
            mongo_documents = []
            for activity_id, group in grouped:
                document = {
                    "activity_id": int(activity_id),
                    "activity_label": activities_dict.get(activity_id, "unknown"),
                    "subject": subject,
                    "split": split_name,
                    "imu_location": loc,
                    "sensor": "AccGyr",
                    "sr": 100,
                    "data": {
                        "acc_x": group[cols['acc'][0]].tolist(),
                        "acc_y": group[cols['acc'][1]].tolist(),
                        "acc_z": group[cols['acc'][2]].tolist(),
                        "gyr_x": group[cols['gyr'][0]].tolist(),
                        "gyr_y": group[cols['gyr'][1]].tolist(),
                        "gyr_z": group[cols['gyr'][2]].tolist()
                    },
                    "datetime": datetime.now()
                }
                mongo_documents.append(document)
            
            # Insertion into the database per file and location
            if mongo_documents:
                collection.insert_many(mongo_documents)
        
        # Memory cleanup
        del df


# Opening connection to MongoDB and uploading all data
with open("config.yml") as file:
    config = yaml.load(file, Loader=yaml.FullLoader)

client = pymongo.MongoClient(config["client"])
db = client[config["db"]]
col = db[config["col"]]
col.delete_many({})

process_and_upload("PAMAP2_Dataset/Protocol", "Protocol", col)
process_and_upload("PAMAP2_Dataset/Optional", "Optional", col)
