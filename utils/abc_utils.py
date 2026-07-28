import pandas as pd


class ABCAnalyzer:

    def __init__(self, dataframe):

        self.df = dataframe.copy()

    def analyze(
            self,
            value_column,
            a_rate=0.80,
            b_rate=0.95):

        self.df = self.df.sort_values(
            by=value_column,
            ascending=False
        )

        self.df.reset_index(drop=True, inplace=True)

        total = self.df[value_column].sum()

        self.df["金额占比"] = self.df[value_column] / total

        self.df["累计占比"] = self.df["金额占比"].cumsum()

        result = []

        for value in self.df["累计占比"]:

            if value <= a_rate:

                result.append("A")

            elif value <= b_rate:

                result.append("B")

            else:

                result.append("C")

        self.df["ABC分类"] = result

        return self.df

    def statistics(self):

        return self.df["ABC分类"].value_counts().to_dict()