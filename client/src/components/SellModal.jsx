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

function SellModal({ isOpen, onClose, AvailableRisk, UsedRisk, symbol }) {
  const targetRef = useRef(null);
  const { moveProps } = useDraggable({ targetRef, isDisabled: !isOpen });

  const sendSellOrder = async () => {
    const response = await axios.get(
      `http://localhost:8000/api/order/exit?symbol=${symbol}`
    );
    console.log(response);
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
              Exit {symbol}
            </ModalHeader>
            <ModalBody>
              <div className="flex items-center justify-between gap-1">
                <p>Available Risk: {AvailableRisk?.toFixed(2)}</p>
                <p>Used Risk: {UsedRisk?.toFixed(2)}</p>
              </div>
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
                color="danger"
                onPress={() => {
                  sendSellOrder();

                  onClose();
                }}
              >
                Sell
              </Button>
            </ModalFooter>
          </>
        )}
      </ModalContent>
    </Modal>
  );
}

export default SellModal;
