import React from "react";
import axios from "axios";
import {
  Navbar,
  NavbarBrand,
  NavbarContent,
  NavbarItem,
  NavbarMenuToggle,
  NavbarMenu,
  NavbarMenuItem,
  Button,
  ButtonGroup,
} from "@nextui-org/react";
import TickerComponent from "./TickerComponent";

import { Link } from "react-router-dom";

import { useLocation } from "react-router-dom";

export default function NavbarComponent() {
  const [isMenuOpen, setIsMenuOpen] = React.useState(false);

  const location = useLocation();

  const currentPath = location.pathname;

  const redirectToZerodhaLogin = () => {
    window.location.href = "http://localhost:8000/api/auth";
  };

  const getIndicesData = async () => {
    let indices = [
      {
        symbol: "NIFTY 50",
        Token: 256265,
      },
      {
        symbol: "NIFTY NEXT 50",
        Token: 270857,
      },
      {
        symbol: "NIFTY BANK",
        Token: 260105,
      },
      {
        symbol: "NIFTY MIDCAP 150",
        Token: 266249,
      },
      {
        symbol: "NIFTY SMLCAP 250",
        Token: 267273,
      },
      {
        symbol: "NIFTY 100",
        Token: 260617,
      },
      {
        symbol: "NIFTY IT",
        Token: 259849,
      },
      {
        symbol: "NIFTY REALTY",
        Token: 261129,
      },
      {
        symbol: "NIFTY INFRA",
        Token: 261385,
      },
      {
        symbol: "NIFTY ENERGY",
        Token: 261400,
      },
      {
        symbol: "NIFTY FMCG",
        Token: 261897,
      },
      {
        symbol: "NIFTY PHARMA",
        Token: 262409,
      },
      {
        symbol: "NIFTY PSUBANK",
        Token: 262921,
      },
      {
        symbol: "NIFTY MIDCAP 50",
        Token: 260873,
      },
      {
        symbol: "NIFTY FIN SERVICE",
        Token: 257801,
      },
      {
        symbol: "NIFTY MIDCAP 100",
        Token: 256777,
      },
    ];

    for (let i = 0; i < indices.length; i++) {
      let index = indices[i];
      await axios.get(
        "http://localhost:8000/api/historicaldata/?instrument_token=" +
          index.Token +
          "&interval=60minute&symbol=" +
          index.symbol
      );
    }
  };

  return (
    <>
      <Navbar onMenuOpenChange={setIsMenuOpen}>
        <NavbarContent>
          <NavbarMenuToggle
            aria-label={isMenuOpen ? "Close menu" : "Open menu"}
            className="sm:hidden"
          />
          <NavbarBrand>
            <p className="text-2xl text-inherit">theTerminal</p>
          </NavbarBrand>
        </NavbarContent>

        <NavbarContent className="hidden gap-4 sm:flex" justify="center">
          <NavbarItem className="">
            <Link to="/">
              <Button
                color="secondary"
                variant={currentPath === "/" ? "solid" : "light"}
                className="mx-2"
              >
                Dashboard
              </Button>
            </Link>
            <Link to="/allpositions">
              <Button
                color="secondary"
                className="mx-2"
                variant={currentPath === "/allpositions" ? "solid" : "light"}
              >
                All positions
              </Button>
            </Link>
          </NavbarItem>
        </NavbarContent>
        <NavbarContent justify="end">
          <NavbarItem>
            <Button
              as={Link}
              onClick={redirectToZerodhaLogin}
              color="primary"
              href="#"
              variant="flat"
            >
              Zerodha Login
            </Button>

            <Button onClick={getIndicesData}>Fetch Indices Data</Button>
          </NavbarItem>
        </NavbarContent>
        <NavbarMenu className="text-white bg-black">
          <NavbarMenuItem>
            <Link to="/">Dashboard</Link>
          </NavbarMenuItem>
          <NavbarMenuItem>
            <Link to="/allpositions">All positions</Link>
          </NavbarMenuItem>
          <NavbarMenuItem onClick={getIndicesData}>
            <Button>Fetch Indices Data</Button>
          </NavbarMenuItem>
        </NavbarMenu>
      </Navbar>
      <TickerComponent />
    </>
  );
}
