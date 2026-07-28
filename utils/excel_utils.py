from pathlib import Path
import pandas as pd

class ExcelManager:
    def __init__(self):
        self.df = None
        self.filename = ""

    def load(self, filename):
        self.filename = filename
        if Path(filename).suffix.lower() == ".csv":
            self.df = pd.read_csv(filename)
        else:
            self.df = pd.read_excel(filename)
        return self.df

    def dataframe(self):
        return self.df

    def rows(self):
        return 0 if self.df is None else len(self.df)

    def cols(self):
        return 0 if self.df is None else len(self.df.columns)
