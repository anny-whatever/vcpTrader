import React from "react";
import { Button as MuiButton, CircularProgress, styled } from "@mui/material";
import { motion } from "framer-motion";

// Create a motion-wrapped MUI Button
const MotionButton = motion(
  React.forwardRef((props, ref) => <MuiButton ref={ref} {...props} />)
);

// Style the button with custom attributes
const StyledButton = styled(MotionButton)(({ theme, size, color }) => ({
  position: "relative",
  display: "inline-flex",
  alignItems: "center",
  justifyContent: "center",
  fontWeight: 600,
  lineHeight: 1.5,
  borderRadius: 8,
  transition: `
    background-color 250ms cubic-bezier(0.4, 0, 0.2, 1),
    box-shadow 250ms cubic-bezier(0.4, 0, 0.2, 1),
    border-color 250ms cubic-bezier(0.4, 0, 0.2, 1),
    color 250ms cubic-bezier(0.4, 0, 0.2, 1)
  `,
  padding:
    size === "small" ? "6px 12px" : size === "large" ? "10px 20px" : "8px 16px",
  fontSize:
    size === "small" ? "0.8125rem" : size === "large" ? "1rem" : "0.875rem",
  "& .MuiButton-startIcon": {
    marginRight: 8,
  },
  "& .MuiButton-endIcon": {
    marginLeft: 8,
  },
}));

const Button = React.forwardRef(
  (
    {
      children,
      loading = false,
      disabled = false,
      startIcon,
      endIcon,
      variant = "contained",
      color = "primary",
      size = "medium",
      animate = true,
      fullWidth = false,
      sx = {},
      ...props
    },
    ref
  ) => {
    // Determine loading state visuals
    const isLoading = loading === true;
    const buttonDisabled = disabled || isLoading;

    // Animation variants with spring physics
    const buttonVariants = animate
      ? {
          hover: {
            y: -2,
            boxShadow:
              "0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)",
            transition: {
              type: "spring",
              stiffness: 400,
              damping: 10,
            },
          },
          tap: {
            y: 0,
            scale: 0.98,
            transition: { duration: 0.1 },
          },
        }
      : {};

    // Combine progress indicator with button
    const renderStartIcon = isLoading ? (
      <CircularProgress
        size={size === "small" ? 14 : size === "large" ? 22 : 18}
        color="inherit"
        sx={{ mr: 1 }}
      />
    ) : (
      startIcon
    );

    return (
      <StyledButton
        ref={ref}
        component={motion.button}
        whileHover={!buttonDisabled && animate ? "hover" : undefined}
        whileTap={!buttonDisabled && animate ? "tap" : undefined}
        variants={buttonVariants}
        variant={variant}
        color={color}
        size={size}
        disabled={buttonDisabled}
        startIcon={renderStartIcon}
        endIcon={endIcon}
        fullWidth={fullWidth}
        disableElevation
        sx={sx}
        {...props}
      >
        {children}
      </StyledButton>
    );
  }
);

Button.displayName = "Button";

export default Button;
