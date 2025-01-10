import React from "react";
import {
  Card,
  CardHeader,
  CardBody,
  CardFooter,
  Divider,
  Link,
} from "@nextui-org/react";
import Logo from "../components/Logo";

function FlagCard({ flags }) {
  const formatValue = (value) => {
    if (typeof value === "boolean") {
      return (
        <span className={value ? "text-green-500" : "text-red-500"}>
          {String(value)}
        </span>
      );
    }
    return value;
  };

  const formatKey = (key) => {
    return key
      .replace(/_/g, " ") // Replace underscores with spaces
      .replace(/\b\w/g, (char) => char.toUpperCase()); // Capitalize each word
  };

  return (
    <div className="flex flex-wrap w-full gap-4">
      {flags?.data?.map((flag, index) => (
        <Card className="min-w-[300px]" key={index}>
          <CardHeader className="flex items-end gap-3">
            <Logo />
            <div className="flex flex-col justify-end text-2xl">
              {formatKey(flag.type || `Card ${index + 1}`)}
            </div>
          </CardHeader>
          <Divider />
          <CardBody>
            {Object.entries(flag).map(
              ([key, value]) =>
                key !== "type" && (
                  <p key={key} className="text-lg">
                    <span className="font-light">{formatKey(key)}:</span>{" "}
                    {formatValue(value)}
                  </p>
                )
            )}
          </CardBody>
        </Card>
      ))}
    </div>
  );
}

export default FlagCard;
