# region imports
from AlgorithmImports import *
# endregion


class WheelStrategyAlgorithm(QCAlgorithm):

    def initialize(self):
        self.set_start_date(2020, 3, 18)
        self.set_cash(1_000_000)
        self.set_security_initializer(BrokerageModelSecurityInitializer(self.brokerage_model, FuncSecuritySeeder(self.get_last_known_prices)))
        self._equity = self.add_equity("SPY", data_normalization_mode=DataNormalizationMode.Raw)
        self._otm_threshold = 0.051
        
    def _get_target_contract(self, right, target_price):
        contract_symbols = self.option_chain_provider.get_option_contract_list(self._equity.symbol, self.time)
        expiry = min([s.id.date for s in contract_symbols if s.id.date.date() > self.time.date() + timedelta(30)])
        filtered_symbols = [
            s for s in contract_symbols 
            if (s.id.date == expiry and s.id.option_right == right and 
                (s.id.strike_price <= target_price if right == OptionRight.PUT else s.id.strike_price >= target_price)
            )
        ]
        symbol = sorted(filtered_symbols, key=lambda s: s.id.strike_price, reverse=right == OptionRight.PUT)[0]
        self.add_option_contract(symbol)
        return symbol

    def on_data(self, data):
        if not self.portfolio.invested and self.is_market_open(self._equity.symbol):
            symbol = self._get_target_contract(OptionRight.PUT, self._equity.price * (1-self._otm_threshold))
            self.set_holdings(symbol, -0.2)
        elif [self._equity.symbol] == [symbol for symbol, holding in self.portfolio.items() if holding.invested]:
            symbol = self._get_target_contract(OptionRight.CALL, self._equity.price * (1+self._otm_threshold))
            self.market_order(symbol, -self._equity.holdings.quantity / 100)
