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

function ReduceModal({
  isOpen,
  onClose,
  symbol,
  ltp,
  AvailableRisk,
  UsedRisk,
  currentQuantity,
}) {
  const targetRef = useRef(null);
  const { moveProps } = useDraggable({ targetRef, isDisabled: !isOpen });
  const [quantity, setQuantity] = useState();
  const [qtyPercentage, setQtyPercentage] = useState();
  const [methodPercentage, setMethodPercentageMethod] = useState(false);

  const sendReduceOrder = async (qty = 0, methodPercentage = false) => {
    if (methodPercentage) {
      qty = calculateQtyForPercentage(qtyPercentage);
    }
    const response = await axios.get(
      `http://localhost:8000/api/order/reduce?symbol=${symbol}&qty=${qty}`
    );
    console.log(response);
  };

  const calculateQtyForPercentage = (qtyPercentage) => {
    let qty = (parseInt(qtyPercentage) / 100) * currentQuantity;
    qty = Math.round(qty * 1) / 1;
    return qty;
  };

  useEffect(() => {
    console.log(methodPercentage, quantity, qtyPercentage, ltp);
  }, [methodPercentage, quantity, qtyPercentage, ltp]);

  return (
    <Modal
      ref={targetRef}
      isOpen={isOpen}
      onOpenChange={() => {
        onClose();
        setQtyPercentage(null);
        setQuantity(null);
        setMethodPercentageMethod(false);
      }}
      className="text-white bg-zinc-900"
    >
      <ModalContent>
        {(onClose) => (
          <>
            <ModalHeader {...moveProps} className="flex flex-col gap-1">
              Reduce {symbol}
            </ModalHeader>
            <ModalBody>
              <div className="flex items-center justify-between gap-1">
                <p>Available Risk: {AvailableRisk?.toFixed(2)}</p>
                <p>Used Risk: {UsedRisk?.toFixed(2)}</p>
              </div>
              <div className="flex items-center gap-1text-white">
                Quantity
                <Switch
                  className="mx-3"
                  aria-label="Automatic updates"
                  onValueChange={setMethodPercentageMethod}
                />
                Quantity %
              </div>
              {methodPercentage ? (
                <div className="flex items-center gap-1">
                  <p>Qty percentage %: </p>
                  <Input
                    className="w-24 ml-1"
                    type="number"
                    onChange={(e) => setQtyPercentage(e.target.value)}
                  />
                </div>
              ) : (
                <div className="flex items-center gap-1">
                  <p>Quantity: </p>
                  <Input
                    className="w-24 ml-1"
                    type="number"
                    onChange={(e) => setQuantity(e.target.value)}
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
                  setQtyPercentage(null);
                  setQuantity(null);
                  setMethodPercentageMethod(false);
                }}
              >
                Close
              </Button>
              <Button
                color="success"
                onPress={() => {
                  if (methodPercentage) {
                    sendReduceOrder(
                      quantity,
                      qtyPercentage,
                      ltp,
                      methodPercentage
                    );
                  } else {
                    sendReduceOrder(quantity);
                  }
                  onClose();
                  setQtyPercentage(null);
                  setQuantity(null);
                  setMethodPercentageMethod(false);
                }}
              >
                Reduce
              </Button>
            </ModalFooter>
          </>
        )}
      </ModalContent>
    </Modal>
  );
}

export default ReduceModal;
