import React, { useState } from "react";
import { DataContext } from "../utils/DataContext";
import { useContext, useEffect } from "react";
function TickerComponent() {
  // Get live data from data context
  const { liveData } = useContext(DataContext);

  const [niftyData, setNiftyData] = useState(null);

  useEffect(() => {
    if (!liveData) {
      return;
    } else {
      for (const data of liveData) {
        if (data.instrument_token === 256265) {
          setNiftyData(data);
          // console.log(data);
        }
      }
    }
  }, [liveData]);

  return (
    <>
      <div className="flex w-full justify-evenly h-fit bg-zinc-800">
        <div className="flex w-full justify-evenly">
          <div
            className={
              niftyData?.last_price > niftyData?.ohlc?.close
                ? "text-green-500"
                : "text-red-500"
            }
          >
            Nifty 50: {niftyData?.last_price}
            {}
          </div>
          <div
            className={
              niftyData?.last_price > niftyData?.ohlc?.close
                ? "text-green-500"
                : "text-red-500"
            }
          >
            Change: {niftyData?.change?.toFixed(4)}% (
            {(niftyData?.last_price - niftyData?.ohlc?.close).toFixed(2)})
          </div>
        </div>

        <div className="flex w-full justify-evenly">
          <div className="ltp">Open: {niftyData?.ohlc?.open}</div>
          <div className="ltp">High: {niftyData?.ohlc?.high}</div>
          <div className="ltp">Low: {niftyData?.ohlc?.low}</div>
          <div className="ltp">Close: {niftyData?.ohlc?.close}</div>
        </div>
      </div>
    </>
  );
}

export default TickerComponent;
