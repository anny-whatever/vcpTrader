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
} from "@heroui/react";
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
            <Link to="/screener">
              <Button
                color="secondary"
                className="mx-2"
                variant={currentPath === "/screener" ? "solid" : "light"}
              >
                Screener
              </Button>
            </Link>
          </NavbarItem>
        </NavbarContent>
        <NavbarContent justify="end">
          <NavbarItem>
            <Button
              as={Link}
              onPress={redirectToZerodhaLogin}
              color="primary"
              href="#"
              variant="flat"
            >
              Zerodha Login
            </Button>
          </NavbarItem>
        </NavbarContent>
        <NavbarMenu className="text-white bg-black">
          <NavbarMenuItem>
            <Link to="/">Dashboard</Link>
          </NavbarMenuItem>
          <NavbarMenuItem>
            <Link to="/allpositions">All positions</Link>
          </NavbarMenuItem>
        </NavbarMenu>
      </Navbar>
      <TickerComponent />
    </>
  );
}
