import React, { useEffect, useRef, useState } from "react";
import {
  Modal,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalFooter,
  Button,
  useDraggable,
} from "@heroui/react";
import axios from "axios";

function ChartModal({ isOpen, onClose, symbol, token }) {
  const targetRef = useRef(null);
  const { moveProps } = useDraggable({ targetRef, isDisabled: !isOpen });

  return (
    <Modal
      ref={targetRef}
      isOpen={isOpen}
      onOpenChange={() => {
        onClose();
      }}
      size="5xl"
      className="text-white bg-zinc-900"
    >
      <ModalContent>
        {(onClose) => (
          <>
            <ModalHeader {...moveProps} className="flex flex-col gap-1">
              Chart for {symbol}
            </ModalHeader>
            <ModalBody>
              <iframe
                src={`https://technicalwidget.streak.tech/?utm_source=context-menu&utm_medium=kite&stock=NSE:${symbol}&theme=dark`}
                width="100%"
                height="550"
                className="rounded-lg"
              ></iframe>
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
            </ModalFooter>
          </>
        )}
      </ModalContent>
    </Modal>
  );
}

export default ChartModal;
