import React from "react";
import {
  Box,
  Grid,
  Paper,
  Table as MuiTable,
  TableBody as MuiTableBody,
  TableCell as MuiTableCell,
  TableContainer as MuiTableContainer,
  TableHead as MuiTableHead,
  TableRow as MuiTableRow,
  CircularProgress,
  styled,
  alpha,
} from "@mui/material";

// Compatibility components to provide fallbacks for HeroUI components
// This helps with a gradual transition from HeroUI to Material UI

// Replacement for HeroUI Column
export const Column = ({ children, className, style, ...props }) => (
  <Box
    display="flex"
    flexDirection="column"
    className={className}
    style={style}
    {...props}
  >
    {children}
  </Box>
);

// Replacement for HeroUI Row
export const Row = ({ children, className, style, ...props }) => (
  <Box
    display="flex"
    flexDirection="row"
    className={className}
    style={style}
    {...props}
  >
    {children}
  </Box>
);

// Replacement for HeroUI Item
export const Item = ({ children, className, style, ...props }) => (
  <Box className={className} style={style} {...props}>
    {children}
  </Box>
);

// Replacement for HeroUI Container
export const Container = ({
  children,
  className,
  style,
  maxWidth,
  ...props
}) => (
  <Box
    className={className}
    style={style}
    maxWidth={maxWidth || "lg"}
    mx="auto"
    px={2}
    {...props}
  >
    {children}
  </Box>
);

// Replacement for HeroUI Card
export const CompatCard = ({ children, className, style, ...props }) => (
  <Paper
    elevation={1}
    className={className}
    style={{
      borderRadius: "0.5rem",
      overflow: "hidden",
      ...style,
    }}
    {...props}
  >
    {children}
  </Paper>
);

// Compatibility Grid for layout
export const GridContainer = ({ children, spacing = 2, ...props }) => (
  <Grid container spacing={spacing} {...props}>
    {children}
  </Grid>
);

export const GridItem = ({ children, xs = 12, sm, md, lg, ...props }) => (
  <Grid item xs={xs} sm={sm} md={md} lg={lg} {...props}>
    {children}
  </Grid>
);

// Table compatibility components
export const StyledTableCell = styled(MuiTableCell)(({ theme }) => ({
  padding: theme.spacing(1.5),
  borderBottom: `1px solid ${alpha(theme.palette.divider, 0.1)}`,
  "&.header": {
    backgroundColor: alpha(theme.palette.background.paper, 0.5),
    color: theme.palette.text.secondary,
    fontWeight: 600,
    fontSize: "0.75rem",
    textTransform: "uppercase",
    letterSpacing: "0.05em",
  },
}));

// Table component replacements
export const Table = ({ children, size = "medium", className, ...props }) => (
  <MuiTableContainer
    sx={{
      borderRadius: 2,
      backgroundColor: (theme) => alpha(theme.palette.background.paper, 0.6),
      backdropFilter: "blur(8px)",
      mb: 3,
    }}
  >
    <MuiTable
      size={size}
      sx={{
        borderCollapse: "separate",
        borderSpacing: "0 4px",
      }}
      className={className}
      {...props}
    >
      {children}
    </MuiTable>
  </MuiTableContainer>
);

export const TableHeader = ({ children, ...props }) => (
  <MuiTableHead {...props}>{children}</MuiTableHead>
);

export const TableBody = ({ children, ...props }) => (
  <MuiTableBody {...props}>{children}</MuiTableBody>
);

export const TableRow = ({ children, className, ...props }) => (
  <MuiTableRow
    sx={{
      "&:hover": {
        backgroundColor: (theme) => alpha(theme.palette.action.hover, 0.1),
        transform: "translateY(-1px)",
        transition: "all 0.2s ease",
      },
    }}
    className={className}
    {...props}
  >
    {children}
  </MuiTableRow>
);

export const TableColumn = ({ children, ...props }) => (
  <StyledTableCell className="header" {...props}>
    {children}
  </StyledTableCell>
);

export const TableCell = ({ children, className, ...props }) => (
  <StyledTableCell className={className} {...props}>
    {children}
  </StyledTableCell>
);

// Spinner replacement
export const Spinner = ({ size = "medium", ...props }) => {
  const sizeMap = {
    sm: 20,
    small: 20,
    md: 40,
    medium: 40,
    lg: 60,
    large: 60,
  };

  const spinnerSize = sizeMap[size] || 40;

  return <CircularProgress size={spinnerSize} {...props} />;
};
