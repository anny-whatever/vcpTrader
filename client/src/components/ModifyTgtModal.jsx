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
import { Toaster, toast } from "sonner"; // Import Toaster and toast from Sonner

function ModifyTgtModal({
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
  const [tgtPercentage, setTgtPercentage] = useState();
  const [tgt, setTgt] = useState();

  const sendModigyTgt = async () => {
    try {
      if (modifyMethodPercentage) {
        let tgtByPercentage = calculateTgtForPercentage();
        const response = await axios.get(
          `http://localhost:8000/api/order/change_tgt?symbol=${symbol}&tgt=${tgtByPercentage}`
        );
        console.log(response);
        toast.success(
          response?.data?.message ||
            "Target modified successfully (percentage)!",
          { duration: 5000 }
        );
      } else {
        const response = await axios.get(
          `http://localhost:8000/api/order/change_tgt?symbol=${symbol}&tgt=${tgt}`
        );
        console.log(response);
        toast.success(
          response?.data?.message || "Target modified successfully!",
          { duration: 5000 }
        );
      }
    } catch (error) {
      console.error(error);
      toast.error("Error modifying target.", { duration: 5000 });
    }
  };

  const calculateTgtForPercentage = () => {
    let tgtPoints =
      currentEntryPrice + currentEntryPrice * (parseFloat(tgtPercentage) / 100);
    return tgtPoints;
  };

  return (
    <>
      {/* Toaster renders the notifications */}
      <Toaster position="bottom-right" />
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
                Modify Target for {symbol}
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
                  <div className="flex items-center gap-1">
                    <p>Target:</p>
                    <Input
                      className="w-24 ml-2"
                      type="number"
                      onChange={(e) => setTgt(e.target.value)}
                    />
                  </div>
                ) : (
                  <div className="flex items-center gap-1">
                    <p>Target %:</p>
                    <Input
                      className="w-24 ml-2"
                      type="number"
                      onChange={(e) => setTgtPercentage(e.target.value)}
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
                    sendModigyTgt();
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
    </>
  );
}

export default ModifyTgtModal;
