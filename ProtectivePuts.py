# region imports
from AlgorithmImports import *
# endregion
# ######################################################
# ## Code Seperated for readiability
# ######################################################

class OptionsUtil():

    def __init__(self, algo, theEquity):
        self.algo = algo
        self.InitOptionsAndGreeks(theEquity)
        
    ## Initialize Options settings, chain filters, pricing models, etc
    ## ---------------------------------------------------------------------------
    def InitOptionsAndGreeks(self, theEquity):

        ## 1. Specify the data normalization mode (must be 'Raw' for options)
        theEquity.SetDataNormalizationMode(DataNormalizationMode.Raw)
        
        ## 2. Set Warmup period of at least 30 days
        self.algo.SetWarmup(30, Resolution.Daily)

        ## 3. Set the security initializer to call SetMarketPrice
        self.algo.SetSecurityInitializer(lambda x: x.SetMarketPrice(self.algo.GetLastKnownPrice(x)))

        ## 4. Subscribe to the option feed for the symbol
        theOptionSubscription = self.algo.AddOption(theEquity.Symbol)

        ## 5. set the pricing model, to calculate Greeks and volatility
        theOptionSubscription.PriceModel = OptionPriceModels.CrankNicolsonFD()  # both European & American, automatically
                
        ## 6. Set the function to filter out strikes and expiry dates from the option chain
        theOptionSubscription.SetFilter(self.OptionsFilterFunction)

    ## Buy an OTM Call Option.
    ## Use Delta to select a call contract to buy
    ## ---------------------------------------------------------------------------
    def BuyAnOTMCall(self, theSymbol):
        
        ## Buy a Call expiring 
        callDelta  = float(self.algo.GetParameter("callDelta"))/100
        callDTE    = int(self.algo.GetParameter("callDTE")) 

        callContract = self.SelectContractByDelta(theSymbol, callDelta, callDTE, OptionRight.Call)
        
        # construct an order message -- good for debugging and order rrecords
        # ------------------------------------------------------------------------------    
        #  if( callContract is not None ): # Might need this.... 
        orderMessage = f"Stock @ ${self.algo.CurrentSlice[theSymbol].Close} |" + \
                       f"Buy {callContract.Symbol} "+ \
                       f"({round(callContract.Greeks.Delta,2)} Delta)"
                       
        self.algo.Debug(f"{self.algo.Time} {orderMessage}")
        self.algo.Order(callContract.Symbol, 1, False, orderMessage  )   
           
           
           
    ## Sell an OTM Put Option.
    ## Use Delta to select a put contract to sell
    ## ---------------------------------------------------------------------------
    def SellAnOTMPut(self, theSymbol):
        
        ## Sell a Put expiring in 2 weeks (14 days)
        putDelta  = float(self.algo.GetParameter("putDelta"))/100
        putDTE    = int(self.algo.GetParameter("putDTE")) 

        putContract = self.SelectContractByDelta(theSymbol, putDelta, putDTE, OptionRight.Put)
        
        ## construct an order message -- good for debugging and order rrecords
        orderMessage = f"Stock @ ${self.algo.CurrentSlice[theSymbol].Close} |" + \
                       f"Sell {putContract.Symbol} "+ \
                       f"({round(putContract.Greeks.Delta,2)} Delta)"
                       
        self.algo.Debug(f"{self.algo.Time} {orderMessage}")
        self.algo.Order(putContract.Symbol, -1, False, orderMessage  )   
           
   
    ## Get an options contract that matches the specified criteria:
    ## Underlying symbol, delta, days till expiration, Option right (put or call)
    ## ---------------------------------------------------------------------------
    def SelectContractByDelta(self, symbolArg, strikeDeltaArg, expiryDTE, optionRightArg= OptionRight.Call):

        canonicalSymbol = self.algo.AddOption(symbolArg)
        if(canonicalSymbol.Symbol not in self.algo.CurrentSlice.OptionChains):
            self.algo.Log(f"{self.algo.Time} [Error] Option Chain not found for {canonicalSymbol.Symbol}")
            return
        
        theOptionChain  = self.algo.CurrentSlice.OptionChains[canonicalSymbol.Symbol]
        theExpiryDate   = self.algo.Time + timedelta(days=expiryDTE)
        
        ## Filter the Call/Put options contracts
        filteredContracts = [x for x in theOptionChain if x.Right == optionRightArg] 

        ## Sort the contracts according to their closeness to our desired expiry
        contractsSortedByExpiration = sorted(filteredContracts, key=lambda p: abs(p.Expiry - theExpiryDate), reverse=False)
        closestExpirationDate = contractsSortedByExpiration[0].Expiry                                        
                                            
        ## Get all contracts for selected expiration
        contractsMatchingExpiryDTE = [contract for contract in contractsSortedByExpiration if contract.Expiry == closestExpirationDate]
    
        ## Get the contract with the contract with the closest delta
        closestContract = min(contractsMatchingExpiryDTE, key=lambda x: abs(abs(x.Greeks.Delta)-strikeDeltaArg))

        return closestContract

    ## The options filter function.
    ## Filter the options chain so we only have relevant strikes & expiration dates. 
    ## ---------------------------------------------------------------------------
    def OptionsFilterFunction(self, optionsContractsChain):

        strikeCount  = 30 # no of strikes around underyling price => for universe selection
        minExpiryDTE = 55  # min num of days to expiration => for uni selection
        maxExpiryDTE = 65  # max num of days to expiration => for uni selection
        
        return optionsContractsChain.IncludeWeeklys()\
                                    .Strikes(-strikeCount, strikeCount)\
                                    .Expiration(timedelta(minExpiryDTE), timedelta(maxExpiryDTE))
