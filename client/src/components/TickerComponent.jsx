import React, { useState, useEffect, useContext } from "react";
import { DataContext } from "../utils/DataContext";

function TickerComponent() {
  const { liveData } = useContext(DataContext);
  const [niftyData, setNiftyData] = useState(null);

  useEffect(() => {
    if (!liveData) return;
    for (const data of liveData) {
      // 256265 is the instrument_token for Nifty 50
      if (data.instrument_token === 256265) {
        setNiftyData(data);
        break;
      }
    }
  }, [liveData]);

  // if (!niftyData) {
  //   return null; // or a loading placeholder
  // }

  const isPriceUp = niftyData?.last_price > niftyData?.ohlc?.close;
  const colorClass = isPriceUp ? "text-green-500" : "text-red-500";

  return (
    <div className="flex flex-col items-center w-full gap-4 p-3 text-white justify-evenly sm:p-1 bg-zinc-800 sm:flex-row">
      {niftyData ? (
        <>
          {/* Left block: Always visible */}
          <div className="flex items-center gap-4">
            <div className={colorClass}>
              Nifty 50: {niftyData?.last_price?.toFixed(2)}
            </div>
            <div className={colorClass}>
              Change: {niftyData?.change?.toFixed(2)}% (
              {(niftyData?.last_price - niftyData?.ohlc.close).toFixed(2)})
            </div>
          </div>

          {/* Right block: Hide on phone */}
          <div className="items-center hidden gap-4 sm:flex">
            <div>Open: {niftyData?.ohlc.open}</div>
            <div>High: {niftyData?.ohlc.high}</div>
            <div>Low: {niftyData?.ohlc.low}</div>
            <div>Close: {niftyData?.ohlc.close}</div>
          </div>
        </>
      ) : (
        <div>Market Closed </div>
      )}
    </div>
  );
}

export default TickerComponent;
