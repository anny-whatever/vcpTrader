import React from "react";
import { useState, useEffect, useContext } from "react";
import { DataContext } from "../utils/DataContext";
import { Tabs, Tab } from "@nextui-org/react";

import FlagCard from "../components/FlagCard";
import PositionCard from "../components/PositionsComponent";

function AllPositions() {
  const { positions, flags } = useContext(DataContext);

  return (
    <>
      <div className="flex flex-col m-3 w-fit">
        <Tabs aria-label="Options">
          <Tab key="Flags" title="Flags">
            <FlagCard flags={flags} />
          </Tab>
          <Tab key="Position" title="Position">
            <PositionCard positions={positions} />
          </Tab>
        </Tabs>
      </div>
    </>
  );
}

export default AllPositions;
