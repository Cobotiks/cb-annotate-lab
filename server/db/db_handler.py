import os
import pandas as pd
import uuid
from db.category_handler import create_categories, remove_image_folder, add_image_folder

imageInfoName = "./db/database/imageInfo.csv"
circleRegionInfo = "./db/database/circleRegionInfo.csv"
boxRegionInfo = "./db/database/boxRegionInfo.csv"
polygonInfo = "./db/database/polygonInfo.csv"


def generateUid(id):
    uid = uuid.uuid1() if (id == None) else id
    return uid

# This class is adapted from the image_annotator
# Source: https://github.com/gnamiro/image_annotator

class Module:
    def __init__(self):
        self.imagesInfo = pd.DataFrame(
            columns=[
                "image-name",
                "selected-classes",
                "comment",
                "image-original-height",
                "image-original-width",
                "image-src",
                "processed",
            ]
        )
        self.imageCircleRegions = pd.DataFrame(
            columns=[
                "region-id",
                "image-src",
                "class",
                "comment",
                "tags",
                "rx",
                "ry",
                "rw",
                "rh",
            ]
        )
        self.imageBoxRegions = pd.DataFrame(
            columns=[
                "region-id",
                "image-src",
                "class",
                "comment",
                "tags",
                "x",
                "y",
                "w",
                "h",
            ]
        )
        self.imagePolygonRegions = pd.DataFrame(
            columns=["region-id", "image-src", "class", "comment", "tags", "points"]
        )

        self.readDataFromDatabase()
        pass

    def readDataFromDatabase(self):
        global imageInfoName, circleRegionInfo, boxRegionInfo, polygonInfo

        self.checkFilesExistence(
            (
                (imageInfoName, self.imagesInfo),
                (circleRegionInfo, self.imageCircleRegions),
                (boxRegionInfo, self.imageBoxRegions),
                (polygonInfo, self.imagePolygonRegions),
            )
        )
        self.imagesInfo = pd.read_csv(imageInfoName)
        self.imageCircleRegions = pd.read_csv(circleRegionInfo)
        self.imageBoxRegions = pd.read_csv(boxRegionInfo)
        self.imagePolygonRegions = pd.read_csv(polygonInfo)

    def checkFilesExistence(self, *args):
        global imageInfoName, circleRegionInfo, boxRegionInfo, polygonInfo
        for arguman in args[0]:
            if not os.path.exists(arguman[0]):
                arguman[1].to_csv(arguman[0], index=False)

    def saveRegionInfo(self, type, imageSrc, data):
        def regionType(type):
            if type == "circle":
                return self.circleRegion
            elif type == "box":
                return self.boxRegion
            elif type == "polygon":
                return self.polygonRegion
            else:
                return self.otherRegion

        regionData = {}
        regionData["region-id"] = data["id"]
        regionData["image-src"] = imageSrc
        regionData["class"] = data["cls"]
        regionData["comment"] = data["comment"] if "comment" in data else ""
        tags = data.get("tags")
        if tags is None:
            tags = []
        regionData["tags"] = ";".join(tags)

        regionFunction = regionType(type)
        regionFunction(regionData, data)

        # return regionData

    def updateCsvData(self, csv_path, file_type):
        """
        Updates or replaces a database CSV file based on the provided CSV file.
        
        Args:
            csv_path (str): Path to the full CSV file to be processed
            file_type (str): Type of the database file to update. Must be one of:
                            'image', 'circle', 'box', 'polygon'
            
        Returns:
            bool: True if update was successful, False otherwise
        """
        try:
            # Validate and get target path based on file type
            file_type = file_type.lower()
            if file_type == 'image':
                target_path = imageInfoName
            elif file_type == 'circle':
                target_path = circleRegionInfo
            elif file_type == 'box':
                target_path = boxRegionInfo
            elif file_type == 'polygon':
                target_path = polygonInfo
            else:
                raise ValueError("file_type must be one of: 'image', 'circle', 'box', 'polygon'")
                
            # Check if the source CSV file exists
            if not os.path.exists(csv_path):
                raise FileNotFoundError(f"CSV file at {csv_path} not found.")
                
            # Read the new CSV file
            new_csv_data = pd.read_csv(csv_path)
            
            # If target file doesn't exist in db, create it with new data
            if not os.path.exists(target_path):
                new_csv_data.to_csv(target_path, index=False)
                print(f"New CSV file created in database at {target_path}")
                
                # Update the corresponding DataFrame in memory
                self._update_dataframe_in_memory(file_type, new_csv_data)
                return True
                
            # Read the existing file
            existing_data = pd.read_csv(target_path)
            
            # Check if the CSV data has the same structure
            if set(new_csv_data.columns) == set(existing_data.columns):
                # Get the appropriate ID column based on file type
                id_column = self._get_id_column(file_type)
                        
                if id_column and id_column in new_csv_data.columns:
                    # Create a merged dataset
                    merged_data = pd.merge(
                        existing_data,
                        new_csv_data,
                        on=id_column,
                        how='outer',
                        suffixes=('_old', '')
                    )
                    
                    # For each row, prefer the new data if available
                    for col in existing_data.columns:
                        if col != id_column:
                            col_old = f"{col}_old"
                            if col_old in merged_data.columns:
                                merged_data[col] = merged_data[col].fillna(merged_data[col_old])
                                merged_data.drop(columns=[col_old], inplace=True)
                    
                    # Save the updated data
                    merged_data.to_csv(target_path, index=False)
                    print(f"CSV at {target_path} updated successfully with merged data")
                    
                    # Update the corresponding DataFrame in memory
                    self._update_dataframe_in_memory(file_type, merged_data)
                else:
                    # If no matching ID column found, replace the entire file
                    new_csv_data.to_csv(target_path, index=False)
                    print(f"CSV at {target_path} replaced with new data (no matching ID column found)")
                    
                    # Update the corresponding DataFrame in memory
                    self._update_dataframe_in_memory(file_type, new_csv_data)
            else:
                # If column structures don't match, replace the entire file
                new_csv_data.to_csv(target_path, index=False)
                print(f"CSV at {target_path} replaced with new data (different column structure)")
                
                # Update the corresponding DataFrame in memory
                self._update_dataframe_in_memory(file_type, new_csv_data)
                
            return True
            
        except Exception as e:
            print(f"Error updating CSV data: {e}")
            return False

    def _get_id_column(self, file_type):
        """Helper method to determine the ID column based on the file type."""
        if file_type == 'image':
            return "image-src"
        elif file_type in {'circle', 'box', 'polygon'}:
            return "region-id"
        return None

    def _update_dataframe_in_memory(self, file_type, new_data):
        """Helper method to update the corresponding DataFrame in memory."""
        if file_type == 'image':
            self.imagesInfo = new_data.copy()
        elif file_type == 'circle':
            self.imageCircleRegions = new_data.copy()
        elif file_type == 'box':
            self.imageBoxRegions = new_data.copy()
        elif file_type == 'polygon':
            self.imagePolygonRegions = new_data.copy()
    def saveRegionInDB(
        self, database, idColumn, uid, data, status
    ):  # TODO if region then use one or zero changeSatus, remove in their
        print(f"Database: {database}")
        index = self.findInfoInDb(database, idColumn, uid)

        if index is not None:  # set -> diff -> list
            # Ensure 'selected-classes' is a string before splitting
            print(f"Updating existing data in database: {data}")
            selected_classes_str = data.get("selected-classes", data["class"])

            print(f"selected_classes_str: {selected_classes_str}")
            if (
                isinstance(selected_classes_str, list)
                and len(selected_classes_str) == 1
                and isinstance(selected_classes_str[0], str)
            ):
                selected_classes_str = selected_classes_str[0]

            if "selected-classes" in data:
                if ";" in selected_classes_str:
                    old_cat_set = set(
                        database.loc[index, "selected-classes"].split(";")
                    )
                    # Split the strings to create sets
                    new_cat_set = set(selected_classes_str.split(";"))
                else:
                    old_cat_set = set(database.loc[index, "selected-classes"])
                    # Split the strings to create sets
                    new_cat_set = set(selected_classes_str)
            else:
                old_cat_set = set(database.loc[index, "class"])
                # Split the strings to create sets
                new_cat_set = set(selected_classes_str)

            for key, value in data.items():
                _value = value[0] if status == 0 else value
                database.at[index, key] = _value

            add_, remove_ = get_lists_absolute(new_cat_set, old_cat_set)
            if "image-name" in data:
                for new_ in add_:
                    add_image_folder(new_, data["image-name"][0], data["image-src"][0])

                for old_ in remove_:
                    remove_image_folder(
                        old_,
                        data["image-name"][0],
                    )

        else:  # add whole cat
            if isinstance(data, dict):
                df = pd.DataFrame.from_dict([data])
            else:
                df = pd.DataFrame(data)
            database = pd.concat([database, df], ignore_index=True)
            print(f"Adding new data to database: {data}")
            if "selected-classes" in data:
                selected_classes = data["selected-classes"]

                # Handle the case where selected_classes is a list containing a single string
                if (
                    isinstance(selected_classes, list)
                    and len(selected_classes) == 1
                    and isinstance(selected_classes[0], str)
                ):
                    selected_classes = selected_classes[0].split(";")

                for class_ in selected_classes:
                    if class_ != "":
                        print(f"selected class: {class_}")
                        add_image_folder(
                            class_, data["image-name"][0], data["image-src"][0]
                        )

            # if 'class' in data:
            # for class_ in data['class']:
            # print(f"class: {class_}")
            # image_name = os.path.basename(data['image-src'][0])
            # if class_ != '':
            #     add_image_folder(class_, image_name,data['image-src'][0])

        return database

    def circleRegion(self, regionData, data):
        coords = data["coords"]
        regionData["rx"] = [coords["rx"]]
        regionData["ry"] = [coords["ry"]]
        regionData["rw"] = [coords["rw"]]
        regionData["rh"] = [coords["rh"]]

        self.imageCircleRegions = self.saveRegionInDB(
            self.imageCircleRegions, "region-id", regionData["region-id"], regionData, 1
        )

    def boxRegion(self, regionData, data):
        coords = data["coords"]
        regionData["x"] = [coords["x"]]
        regionData["y"] = [coords["y"]]
        regionData["w"] = [coords["w"]]
        regionData["h"] = [coords["h"]]

        self.imageBoxRegions = self.saveRegionInDB(
            self.imageBoxRegions, "region-id", regionData["region-id"], regionData, 1
        )

    def polygonRegion(self, regionData, data):
        regionData["points"] = ";".join(
            e
            for e in [
                "-".join(str(coord) for coord in point) for point in data["points"]
            ]
        )
        self.imagePolygonRegions = self.saveRegionInDB(
            self.imagePolygonRegions,
            "region-id",
            regionData["region-id"],
            regionData,
            1,
        )

    def otherRegion(self, regionData, data):
        print(f"This region type is not defined yet: {data['type']}")

    def getImageData(self, data):
        imageData = {}
        imageData["image-name"] = [data["name"]]
        imageData["image-src"] = [data["src"]]
        imageData["comment"] = [data["comment"]]
        imageData["selected-classes"] = [";".join(data["cls"])]
        pixelSize = data["pixelSize"] if "pixelSize" in data else {}
        imageData["image-original-height"] = [pixelSize["h"]] if pixelSize != {} else []
        imageData["image-original-width"] = [pixelSize["w"]] if pixelSize != {} else []
        imageData["processed"] = [1]
        return imageData

    def findInfoInDb(self, database, uid_columns, uid):
        idx = database[database[uid_columns] == uid].index.values
        if len(idx) > 0:
            return idx[0]

        return None

    def findInfoInPolygonDb(self, database, uid_columns, uid):
        regions = database[database[uid_columns] == uid]
        if len(regions) > 0:
            return regions

        return None

    def findInfoInBoxDb(self, database, uid_columns, uid):
        regions = database[database[uid_columns] == uid]
        if len(regions) > 0:
            return regions

        return None

    def findInfoInCircleDb(self, database, uid_columns, uid):
        regions = database[database[uid_columns] == uid]
        if len(regions) > 0:
            return regions

        return None

    def saveDataAutomatically(self, *args):
        for arguman in args[0]:
            arguman[1].to_csv(arguman[0], index=False)

    def handleNewData(self, data):
        try:
            imageData = self.getImageData(data)
            self.imagesInfo = self.saveRegionInDB(
                self.imagesInfo, "image-src", imageData["image-src"][0], imageData, 0
            )

            existingCircleRegions = self.imageCircleRegions[
                self.imageCircleRegions["image-src"] == data["src"]
            ]
            existingBoxRegions = self.imageBoxRegions[
                self.imageBoxRegions["image-src"] == data["src"]
            ]
            existingPolygonRegions = self.imagePolygonRegions[
                self.imagePolygonRegions["image-src"] == data["src"]
            ]

            newRegionIds = {region["id"] for region in data["regions"]}
            existingRegionIds = (
                set(existingCircleRegions["region-id"])
                .union(set(existingBoxRegions["region-id"]))
                .union(set(existingPolygonRegions["region-id"]))
            )

            # Remove regions that are not present in the new data
            regionsToRemove = existingRegionIds - newRegionIds
            self.imageCircleRegions = self.imageCircleRegions[
                ~self.imageCircleRegions["region-id"].isin(regionsToRemove)
            ]
            self.imageBoxRegions = self.imageBoxRegions[
                ~self.imageBoxRegions["region-id"].isin(regionsToRemove)
            ]
            self.imagePolygonRegions = self.imagePolygonRegions[
                ~self.imagePolygonRegions["region-id"].isin(regionsToRemove)
            ]

            # Add or update regions
            for region in data["regions"]:
                self.saveRegionInfo(region["type"], data["src"], region)

            self.saveDataAutomatically(
                (
                    (imageInfoName, self.imagesInfo),
                    (circleRegionInfo, self.imageCircleRegions),
                    (boxRegionInfo, self.imageBoxRegions),
                    (polygonInfo, self.imagePolygonRegions),
                )
            )
            return True
        except Exception as e:
            print("Error:", e)
            return False

    def handleActiveImageData(self, data):
        try:
            imageData = self.getImageData(data)
            self.imagesInfo = self.saveRegionInDB(
                self.imagesInfo, "image-src", imageData["image-src"][0], imageData, 0
            )
            self.imagesInfo.to_csv(imageInfoName, index=False)
            return True  # Return True if data was successfully handled
        except Exception as e:
            print("Error:", e)
            return False  # Return False if an error occurred while handling the data

    def createCategories(self, labels):
        if labels is None:
            return
        create_categories(labels)

    def clear_db(self):
        try:
            # Drop all rows from DataFrames
            self.imagesInfo.drop(self.imagesInfo.index, inplace=True)
            self.imageCircleRegions.drop(self.imageCircleRegions.index, inplace=True)
            self.imageBoxRegions.drop(self.imageBoxRegions.index, inplace=True)
            self.imagePolygonRegions.drop(self.imagePolygonRegions.index, inplace=True)

            # Save updated DataFrames back to CSV files
            self.imagesInfo.to_csv(imageInfoName, index=False)
            self.imageCircleRegions.to_csv(circleRegionInfo, index=False)
            self.imageBoxRegions.to_csv(boxRegionInfo, index=False)
            self.imagePolygonRegions.to_csv(polygonInfo, index=False)

            print("DataFrames cleared and CSV files updated.")

        except Exception as e:
            print(f"Error occurred: {e}")

    def get_class_distribution(self):
        class_counts = pd.Series(dtype=int)

        # Count classes in each DataFrame
        class_counts = class_counts.add(
            self.imageCircleRegions["class"].value_counts(), fill_value=0
        )
        class_counts = class_counts.add(
            self.imageBoxRegions["class"].value_counts(), fill_value=0
        )
        class_counts = class_counts.add(
            self.imagePolygonRegions["class"].value_counts(), fill_value=0
        )

        # Convert the series to a dictionary and return
        return class_counts.to_dict()

    def __str__(self):
        return "database"


def get_lists_absolute(new_set, old_set):
    return list(new_set - old_set), list(old_set - new_set)
