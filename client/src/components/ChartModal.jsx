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

  const openChart = (symbol, instrument_token) => {
    window.open(
      `https://kite.zerodha.com/chart/ext/tvc/NSE/${symbol}/${instrument_token}?theme=dark`,
      "_blank"
    );
  };

  return (
    <Modal
      ref={targetRef}
      isOpen={isOpen}
      onOpenChange={() => {
        onClose();
      }}
      size="5xl"
      className="text-white bg-[#1b1b1b]"
    >
      <ModalContent>
        {(onClose) => (
          <>
            <ModalHeader
              {...moveProps}
              className="flex flex-wrap items-center justify-between"
            >
              Chart for {symbol}
              <Button
                color="warning"
                variant="flat"
                className="mr-4"
                onPress={() => {
                  openChart(symbol, token);
                }}
              >
                Open full chart
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                  strokeWidth={1.5}
                  stroke="currentColor"
                  className="size-5"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M3.75 3v11.25A2.25 2.25 0 0 0 6 16.5h2.25M3.75 3h-1.5m1.5 0h16.5m0 0h1.5m-1.5 0v11.25A2.25 2.25 0 0 1 18 16.5h-2.25m-7.5 0h7.5m-7.5 0-1 3m8.5-3 1 3m0 0-.5 1.5m-.5-1.5h-9.5m0 0-.5 1.5m.75-9 3-3 2.148 2.148A12.061 12.061 0 0 1 16.5 7.605"
                  />
                </svg>
              </Button>
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
