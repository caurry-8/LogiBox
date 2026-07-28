import math

class EOQCalculator:
    def __init__(self, demand, order_cost, hold_cost):
        self.demand = demand
        self.order_cost = order_cost
        self.hold_cost = hold_cost

    def validate(self):
        if self.demand <= 0:
            raise ValueError("年需求量必须大于 0。")
        if self.order_cost <= 0:
            raise ValueError("每次订货成本必须大于 0。")
        if self.hold_cost <= 0:
            raise ValueError("单位持有成本必须大于 0。")

    def eoq(self):
        self.validate()
        return math.sqrt(2 * self.demand * self.order_cost / self.hold_cost)

    def order_times(self):
        return self.demand / self.eoq()

    def order_cycle(self):
        return 365 / self.order_times()

    def average_inventory(self):
        return self.eoq() / 2

    def ordering_cost(self):
        return self.order_times() * self.order_cost

    def holding_cost(self):
        return self.average_inventory() * self.hold_cost

    def total_cost(self):
        return self.ordering_cost() + self.holding_cost()

    def report(self):
        return {
            "EOQ": round(self.eoq(), 2),
            "平均库存": round(self.average_inventory(), 2),
            "订货次数": round(self.order_times(), 2),
            "订货周期": round(self.order_cycle(), 2),
            "年订货成本": round(self.ordering_cost(), 2),
            "年库存持有成本": round(self.holding_cost(), 2),
            "总成本": round(self.total_cost(), 2),
        }
