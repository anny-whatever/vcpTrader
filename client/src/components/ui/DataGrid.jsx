import React, { useState } from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TableSortLabel,
  TablePagination,
  Paper,
  Box,
  Input,
  InputAdornment,
  Typography,
  Chip,
  IconButton,
  styled,
  alpha,
} from "@mui/material";
import { motion, AnimatePresence } from "framer-motion";
import SearchIcon from "@mui/icons-material/Search";
import TuneIcon from "@mui/icons-material/Tune";
import ArrowDropUpIcon from "@mui/icons-material/ArrowDropUp";
import ArrowDropDownIcon from "@mui/icons-material/ArrowDropDown";

// Styled components
const StyledTableContainer = styled(TableContainer)(({ theme }) => ({
  borderRadius: 16,
  backgroundColor: alpha(theme.palette.background.paper, 0.6),
  backdropFilter: "blur(8px)",
  overflow: "hidden",
  "&::-webkit-scrollbar": {
    width: "8px",
    height: "8px",
  },
  "&::-webkit-scrollbar-track": {
    background: alpha(theme.palette.background.paper, 0.05),
    borderRadius: "10px",
  },
  "&::-webkit-scrollbar-thumb": {
    background: alpha(theme.palette.primary.main, 0.2),
    borderRadius: "10px",
    "&:hover": {
      background: alpha(theme.palette.primary.main, 0.3),
    },
  },
}));

const StyledTableHead = styled(TableHead)(({ theme }) => ({
  position: "sticky",
  top: 0,
  backgroundColor: alpha(theme.palette.background.paper, 0.8),
  backdropFilter: "blur(8px)",
  zIndex: 2,
  borderBottom: `1px solid ${alpha(theme.palette.divider, 0.1)}`,
}));

const StyledTableCell = styled(TableCell)(({ theme, head, highlight }) => ({
  padding: theme.spacing(1.5),
  borderBottom: head
    ? "none"
    : `1px solid ${alpha(theme.palette.divider, 0.05)}`,
  color: head ? theme.palette.text.secondary : theme.palette.text.primary,
  fontSize: head ? "0.75rem" : "0.875rem",
  fontWeight: head || highlight ? 600 : 400,
  textTransform: head ? "uppercase" : "none",
  letterSpacing: head ? "0.05em" : "normal",
  whiteSpace: "nowrap",
  overflow: "hidden",
  textOverflow: "ellipsis",
  maxWidth: "200px", // Prevent cells from stretching too wide
}));

const StyledTableRow = styled(TableRow)(({ theme, clickable }) => ({
  position: "relative",
  transition: "all 0.2s ease",
  backgroundColor: "transparent",
  "&:hover": {
    backgroundColor: clickable
      ? alpha(theme.palette.primary.main, 0.05)
      : "transparent",
    transform: clickable ? "translateY(-1px)" : "none",
    boxShadow: clickable ? `0 4px 8px -2px ${alpha("#000", 0.1)}` : "none",
    zIndex: 1,
  },
  cursor: clickable ? "pointer" : "default",
}));

const SearchInput = styled(Input)(({ theme }) => ({
  backgroundColor: alpha(theme.palette.background.paper, 0.5),
  backdropFilter: "blur(8px)",
  borderRadius: 8,
  padding: theme.spacing(0.5, 1),
  "&:hover": {
    backgroundColor: alpha(theme.palette.background.paper, 0.7),
  },
  "& .MuiInputBase-input": {
    padding: theme.spacing(0.75, 0),
  },
  "&::before, &::after": {
    display: "none",
  },
}));

const FilterChip = styled(Chip)(({ theme }) => ({
  margin: theme.spacing(0, 0.5),
  height: 28,
  borderRadius: 14,
  "& .MuiChip-label": {
    paddingLeft: 8,
    paddingRight: 8,
  },
}));

// Define DataGrid component
const DataGrid = ({
  columns = [],
  data = [],
  rowKey = "id",
  onRowClick,
  pagination = false,
  initialSortField = null,
  initialSortDirection = "asc",
  searchable = false,
  searchFields = [],
  loading = false,
  emptyMessage = "No data to display",
  hideHeader = false,
  hover = true,
  sx = {},
}) => {
  // State for sorting
  const [sortField, setSortField] = useState(initialSortField);
  const [sortDirection, setSortDirection] = useState(initialSortDirection);

  // State for pagination
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);

  // State for search
  const [searchTerm, setSearchTerm] = useState("");

  // Handle sort changes
  const handleSort = (field) => {
    const isAsc = sortField === field && sortDirection === "asc";
    setSortDirection(isAsc ? "desc" : "asc");
    setSortField(field);
  };

  // Filter data based on search term
  const filteredData =
    searchTerm && searchable && searchFields.length > 0
      ? data.filter((row) => {
          return searchFields.some((field) => {
            const value = row[field];
            if (value == null) return false;
            return String(value)
              .toLowerCase()
              .includes(searchTerm.toLowerCase());
          });
        })
      : data;

  // Sort data based on sort field and direction
  const sortedData = sortField
    ? [...filteredData].sort((a, b) => {
        const valueA = a[sortField];
        const valueB = b[sortField];

        if (valueA === valueB) return 0;
        if (valueA == null) return 1;
        if (valueB == null) return -1;

        if (typeof valueA === "number" && typeof valueB === "number") {
          return sortDirection === "asc" ? valueA - valueB : valueB - valueA;
        }

        const strA = String(valueA).toLowerCase();
        const strB = String(valueB).toLowerCase();

        return sortDirection === "asc"
          ? strA.localeCompare(strB)
          : strB.localeCompare(strA);
      })
    : filteredData;

  // Apply pagination
  const paginatedData = pagination
    ? sortedData.slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage)
    : sortedData;

  // Handle page change
  const handleChangePage = (event, newPage) => {
    setPage(newPage);
  };

  // Handle rows per page change
  const handleChangeRowsPerPage = (event) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };

  // Handle search term change
  const handleSearchChange = (event) => {
    setSearchTerm(event.target.value);
    setPage(0); // Reset to first page when searching
  };

  // Row animation variants
  const rowVariants = {
    hidden: { opacity: 0, y: 10 },
    visible: (i) => ({
      opacity: 1,
      y: 0,
      transition: {
        delay: i * 0.05,
        duration: 0.2,
        ease: [0.25, 0.1, 0.25, 1.0],
      },
    }),
    exit: { opacity: 0, y: -10, transition: { duration: 0.1 } },
  };

  return (
    <Box sx={{ width: "100%", ...sx }}>
      {/* Toolbar with search and filters */}
      {searchable && (
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            mb: 2,
            flexWrap: "wrap",
            gap: 1,
          }}
        >
          <Box sx={{ display: "flex", alignItems: "center" }}>
            <SearchInput
              placeholder="Search..."
              startAdornment={
                <InputAdornment position="start">
                  <SearchIcon fontSize="small" />
                </InputAdornment>
              }
              value={searchTerm}
              onChange={handleSearchChange}
              autoComplete="off"
            />
            <IconButton size="small" sx={{ ml: 1 }}>
              <TuneIcon fontSize="small" />
            </IconButton>
          </Box>
        </Box>
      )}

      {/* Data grid */}
      <StyledTableContainer component={Paper} elevation={0}>
        <Table size="small" aria-label="data table">
          {!hideHeader && (
            <StyledTableHead>
              <TableRow>
                {columns.map((column) => (
                  <StyledTableCell
                    key={column.field}
                    head={true}
                    align={column.align || "left"}
                    style={{ width: column.width, minWidth: column.minWidth }}
                  >
                    {column.sortable !== false && (
                      <TableSortLabel
                        active={sortField === column.field}
                        direction={
                          sortField === column.field ? sortDirection : "asc"
                        }
                        onClick={() => handleSort(column.field)}
                        IconComponent={
                          sortDirection === "asc"
                            ? ArrowDropUpIcon
                            : ArrowDropDownIcon
                        }
                      >
                        {column.headerName}
                      </TableSortLabel>
                    )}
                    {column.sortable === false && column.headerName}
                  </StyledTableCell>
                ))}
              </TableRow>
            </StyledTableHead>
          )}
          <TableBody>
            <AnimatePresence>
              {paginatedData.length > 0 ? (
                paginatedData.map((row, index) => (
                  <StyledTableRow
                    component={motion.tr}
                    variants={rowVariants}
                    initial="hidden"
                    animate="visible"
                    exit="exit"
                    custom={index}
                    key={row[rowKey] || index}
                    clickable={!!onRowClick}
                    onClick={onRowClick ? () => onRowClick(row) : undefined}
                    hover={hover}
                  >
                    {columns.map((column) => (
                      <StyledTableCell
                        key={`${row[rowKey]}-${column.field}`}
                        align={column.align || "left"}
                        highlight={column.highlight}
                      >
                        {column.renderCell
                          ? column.renderCell({ value: row[column.field], row })
                          : row[column.field]}
                      </StyledTableCell>
                    ))}
                  </StyledTableRow>
                ))
              ) : (
                <TableRow>
                  <TableCell
                    colSpan={columns.length}
                    align="center"
                    sx={{ py: 4 }}
                  >
                    <Typography variant="body2" color="text.secondary">
                      {emptyMessage}
                    </Typography>
                  </TableCell>
                </TableRow>
              )}
            </AnimatePresence>
          </TableBody>
        </Table>
      </StyledTableContainer>

      {/* Pagination */}
      {pagination && filteredData.length > 0 && (
        <TablePagination
          rowsPerPageOptions={[5, 10, 25, 50]}
          component="div"
          count={filteredData.length}
          rowsPerPage={rowsPerPage}
          page={page}
          onPageChange={handleChangePage}
          onRowsPerPageChange={handleChangeRowsPerPage}
          sx={{
            ".MuiTablePagination-toolbar": {
              paddingLeft: 1,
            },
            ".MuiTablePagination-selectLabel, .MuiTablePagination-displayedRows":
              {
                fontSize: "0.75rem",
              },
          }}
        />
      )}
    </Box>
  );
};

export default DataGrid;
