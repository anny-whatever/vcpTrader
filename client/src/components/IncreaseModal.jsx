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

function IncreaseModal({
  isOpen,
  onClose,
  AvailableRisk,
  UsedRisk,
  symbol,
  ltp,
}) {
  const targetRef = useRef(null);
  const { moveProps } = useDraggable({ targetRef, isDisabled: !isOpen });
  const [quantity, setQuantity] = useState();
  const [intendedRisk, setIntendedRisk] = useState();
  const [methodRiskPoolMethod, setMethodRiskPoolMethod] = useState(false);

  const sendIncreaseOrder = async (
    qty = 0,
    intendedRisk = 0,
    ltp = 0,
    methodRiskPoolMethod = false
  ) => {
    if (methodRiskPoolMethod) {
      qty = calculateQtyForRiskPool(intendedRisk, ltp);
    }
    const response = await axios.get(
      `http://localhost:8000/api/order/increase?symbol=${symbol}&qty=${qty}`
    );
    console.log(response);
  };

  const calculateQtyForRiskPool = (intendedRisk, ltp) => {
    const absoluteRisk =
      (AvailableRisk + UsedRisk) * (parseInt(intendedRisk) / 100);
    const sl = ltp - ltp * 0.1;
    const slPoints = ltp - sl;
    let qty = absoluteRisk / slPoints;
    qty = Math.round(qty * 1) / 1;
    return qty;
  };

  useEffect(() => {
    console.log(methodRiskPoolMethod, quantity, intendedRisk, ltp);
  }, [methodRiskPoolMethod, quantity, intendedRisk, ltp]);

  return (
    <Modal
      ref={targetRef}
      isOpen={isOpen}
      onOpenChange={() => {
        onClose();
        setIntendedRisk(null);
        setQuantity(null);
        setMethodRiskPoolMethod(false);
      }}
      className="text-white bg-zinc-900"
    >
      <ModalContent>
        {(onClose) => (
          <>
            <ModalHeader {...moveProps} className="flex flex-col gap-1">
              Increase {symbol}
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
                  onValueChange={setMethodRiskPoolMethod}
                />
                Risk pool %
              </div>
              {methodRiskPoolMethod ? (
                <div className="flex items-center gap-1">
                  <p>Risk pool %: </p>
                  <Input
                    className="w-24 ml-1"
                    type="number"
                    onChange={(e) => setIntendedRisk(e.target.value)}
                  />
                </div>
              ) : (
                <div className="flex items-center justify-between gap-1">
                  <div className="flex items-center gap-1">
                    <p>Quantity: </p>
                    <Input
                      className="w-24 ml-1"
                      type="number"
                      onChange={(e) => setQuantity(e.target.value)}
                    />
                  </div>
                  <div className="flex items-center gap-1">
                    Cost: {quantity ? (quantity * ltp).toFixed(2) : 0}
                  </div>
                </div>
              )}
            </ModalBody>
            <ModalFooter>
              <Button
                color="danger"
                variant="light"
                onPress={() => {
                  onClose();
                  setIntendedRisk(null);
                  setQuantity(null);
                  setMethodRiskPoolMethod(false);
                }}
              >
                Close
              </Button>
              <Button
                color="success"
                onPress={() => {
                  if (methodRiskPoolMethod) {
                    sendIncreaseOrder(
                      quantity,
                      intendedRisk,
                      ltp,
                      methodRiskPoolMethod
                    );
                  } else {
                    sendIncreaseOrder(quantity);
                  }
                  onClose();
                  setIntendedRisk(null);
                  setQuantity(null);
                  setMethodRiskPoolMethod(false);
                }}
              >
                Buy
              </Button>
            </ModalFooter>
          </>
        )}
      </ModalContent>
    </Modal>
  );
}

export default IncreaseModal;
