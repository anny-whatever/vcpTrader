import React, { useEffect, useRef, useState } from "react";
import {
  Modal,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalFooter,
  Button,
  useDraggable,
  Input,
  Switch,
} from "@heroui/react";
import axios from "axios";

function ModifySlModal({
  isOpen,
  onClose,
  AvailableRisk,
  UsedRisk,
  symbol,
  currentEntryPrice,
}) {
  const targetRef = useRef(null);
  const { moveProps } = useDraggable({ targetRef, isDisabled: !isOpen });
  const [modifyMethodPercentage, setModifyMethodPercentage] = useState(false);
  const [sl, setSl] = useState();
  const [slPercentage, setSlPercentage] = useState();

  const sendModifySl = async () => {
    if (modifyMethodPercentage) {
      let slByPercentage = calculateSlForPercentage();
      const response = await axios.get(
        `http://localhost:8000/api/order/change_sl?symbol=${symbol}&sl=${slByPercentage}`
      );
      console.log(response);
    } else {
      const response = await axios.get(
        `http://localhost:8000/api/order/change_sl?symbol=${symbol}&sl=${sl}`
      );
      console.log(response);
    }
  };

  const calculateSlForPercentage = () => {
    let slPoints = currentEntryPrice - currentEntryPrice * (slPercentage / 100);
    return slPoints;
  };

  return (
    <Modal
      ref={targetRef}
      isOpen={isOpen}
      onOpenChange={() => {
        onClose();
      }}
      className="text-white bg-zinc-900"
    >
      <ModalContent>
        {(onClose) => (
          <>
            <ModalHeader {...moveProps} className="flex flex-col gap-1">
              Modify Stop-loss for {symbol}
            </ModalHeader>
            <ModalBody>
              <div className="flex items-center justify-between gap-1">
                <p>Available Risk: {AvailableRisk?.toFixed(2)}</p>
                <p>Used Risk: {UsedRisk?.toFixed(2)}</p>
              </div>
              <div className="flex items-center gap-1text-white">
                Absolute{" "}
                <Switch
                  onChange={() =>
                    setModifyMethodPercentage(!modifyMethodPercentage)
                  }
                  className="mx-2"
                />{" "}
                Percentage
              </div>
              {modifyMethodPercentage === false ? (
                <div className="flex items-center gap-1text-white">
                  Stop-loss:{" "}
                  <Input
                    className="w-24 ml-2"
                    type="number"
                    onChange={(e) => setSl(e.target.value)}
                  />
                </div>
              ) : (
                <div className="flex items-center gap-1text-white">
                  Stop-loss %:{" "}
                  <Input
                    className="w-24 ml-2"
                    type="number"
                    onChange={(e) => setSlPercentage(e.target.value)}
                  />
                </div>
              )}
            </ModalBody>
            <ModalFooter>
              <Button
                color="danger"
                variant="light"
                onPress={() => {
                  onClose();
                }}
              >
                Close
              </Button>
              <Button
                color="secondary"
                onPress={() => {
                  sendModifySl();

                  onClose();
                }}
              >
                Modify
              </Button>
            </ModalFooter>
          </>
        )}
      </ModalContent>
    </Modal>
  );
}

export default ModifySlModal;
