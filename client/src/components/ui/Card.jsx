import React from "react";
import {
  Card as MuiCard,
  CardContent as MuiCardContent,
  CardHeader as MuiCardHeader,
  styled,
} from "@mui/material";
import { motion } from "framer-motion";
import { alpha } from "@mui/material/styles";

// Create motion-wrapped variants of MUI components
const MotionCard = motion(
  React.forwardRef((props, ref) => <MuiCard ref={ref} {...props} />)
);

const MotionCardContent = motion(
  React.forwardRef((props, ref) => <MuiCardContent ref={ref} {...props} />)
);

const MotionCardHeader = motion(
  React.forwardRef((props, ref) => <MuiCardHeader ref={ref} {...props} />)
);

// Styled components
const StyledCard = styled(MotionCard)(({ theme, variant, clickable }) => ({
  position: "relative",
  overflow: "visible", // Allow for shadow animations to be visible outside card
  borderRadius: 16,
  backgroundColor:
    variant === "glass"
      ? alpha(theme.palette.background.paper, 0.7)
      : variant === "outlined"
      ? "transparent"
      : theme.palette.background.paper,
  backdropFilter: variant === "glass" ? "blur(10px)" : "none",
  border:
    variant === "outlined"
      ? `1px solid ${alpha(theme.palette.divider, 0.1)}`
      : "none",
  boxShadow:
    variant === "glass"
      ? `0 8px 32px 0 ${alpha("#000", 0.1)}, 0 0 0 1px ${alpha("#fff", 0.05)}`
      : variant === "elevated"
      ? `0 1px 3px 0 ${alpha("#000", 0.1)}, 0 1px 2px -1px ${alpha(
          "#000",
          0.1
        )}`
      : "none",
  cursor: clickable ? "pointer" : "default",
  transition: "all 0.3s cubic-bezier(0.4, 0, 0.2, 1)",
}));

const StyledCardContent = styled(MotionCardContent)(({ theme, padding }) => ({
  padding:
    padding === "small"
      ? theme.spacing(1.5)
      : padding === "large"
      ? theme.spacing(3)
      : theme.spacing(2),
  "&:last-child": {
    paddingBottom:
      padding === "small"
        ? theme.spacing(1.5)
        : padding === "large"
        ? theme.spacing(3)
        : theme.spacing(2),
  },
}));

const StyledCardHeader = styled(MotionCardHeader)(({ theme, padding }) => ({
  padding:
    padding === "small"
      ? theme.spacing(1.5)
      : padding === "large"
      ? theme.spacing(3)
      : theme.spacing(2),
  "& .MuiCardHeader-title": {
    fontWeight: 600,
  },
}));

// Exposed components
const Card = React.forwardRef(
  (
    {
      children,
      variant = "default",
      clickable = false,
      animate = true,
      hover = true,
      onClick,
      sx = {},
      ...props
    },
    ref
  ) => {
    // Animation variants
    const cardVariants = animate
      ? {
          initial: {
            opacity: 0,
            y: 20,
            scale: 0.98,
          },
          animate: {
            opacity: 1,
            y: 0,
            scale: 1,
            transition: {
              type: "spring",
              damping: 25,
              stiffness: 300,
              duration: 0.3,
            },
          },
          hover:
            clickable && hover
              ? {
                  y: -5,
                  boxShadow: `0 20px 25px -5px ${alpha(
                    "#000",
                    0.15
                  )}, 0 10px 10px -5px ${alpha("#000", 0.1)}`,
                  transition: {
                    type: "spring",
                    stiffness: 300,
                    damping: 15,
                  },
                }
              : {},
          tap: clickable
            ? {
                scale: 0.98,
                y: -2,
                transition: { duration: 0.1 },
              }
            : {},
        }
      : {};

    return (
      <StyledCard
        ref={ref}
        component={motion.div}
        initial={animate ? "initial" : undefined}
        animate={animate ? "animate" : undefined}
        whileHover={clickable && hover && animate ? "hover" : undefined}
        whileTap={clickable && animate ? "tap" : undefined}
        variants={cardVariants}
        variant={variant}
        clickable={clickable}
        onClick={onClick}
        sx={sx}
        {...props}
      >
        {children}
      </StyledCard>
    );
  }
);

const CardContent = React.forwardRef(
  ({ children, padding = "medium", sx = {}, ...props }, ref) => (
    <StyledCardContent ref={ref} padding={padding} sx={sx} {...props}>
      {children}
    </StyledCardContent>
  )
);

const CardHeader = React.forwardRef(
  ({ padding = "medium", sx = {}, ...props }, ref) => (
    <StyledCardHeader
      ref={ref}
      padding={padding}
      disableTypography
      sx={sx}
      {...props}
    />
  )
);

Card.displayName = "Card";
CardContent.displayName = "CardContent";
CardHeader.displayName = "CardHeader";

export { Card, CardContent, CardHeader };
