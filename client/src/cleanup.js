// cleanup.js - Run with Node.js to help clean up HeroUI references
// Usage: node cleanup.js

const fs = require("fs");
const path = require("path");

console.log("Starting cleanup of HeroUI references...");

// Files to modify
const filesToCheck = [];

// Walk through directories recursively
function walkSync(dir, fileList = []) {
  const files = fs.readdirSync(dir);
  files.forEach((file) => {
    const filePath = path.join(dir, file);
    const stat = fs.statSync(filePath);
    if (stat.isDirectory() && file !== "node_modules") {
      walkSync(filePath, fileList);
    } else if (
      stat.isFile() &&
      (file.endsWith(".jsx") || file.endsWith(".js")) &&
      !file.includes("cleanup.js")
    ) {
      fileList.push(filePath);
    }
  });
  return fileList;
}

// Get all JS and JSX files
const sourceDir = path.resolve(__dirname);
const allFiles = walkSync(sourceDir);

console.log(`Found ${allFiles.length} files to check`);

// HeroUI patterns to look for and replace
const patterns = [
  {
    search: /from ['"]@heroui\/react['"]/g,
    replace: "// Removed HeroUI import",
  },
  {
    search: /import\s+{\s*([^}]+)\s*}\s+from\s+['"]@heroui\/react['"]/g,
    replace: "// Removed HeroUI import",
  },
  {
    search: /<HeroUIProvider[^>]*>/g,
    replace: "",
  },
  {
    search: /<\/HeroUIProvider>/g,
    replace: "",
  },
  {
    search: /className="[^"]*dark:[^"]*"/g,
    replace: (match) => match.replace(/dark:[^\s"]+/g, ""),
  },
];

// Process each file
let modifiedCount = 0;
allFiles.forEach((filePath) => {
  try {
    let content = fs.readFileSync(filePath, "utf8");
    let originalContent = content;

    // Apply all replacements
    patterns.forEach((pattern) => {
      content = content.replace(pattern.search, pattern.replace);
    });

    // Save if modified
    if (content !== originalContent) {
      fs.writeFileSync(filePath, content, "utf8");
      console.log(`Modified: ${path.relative(sourceDir, filePath)}`);
      modifiedCount++;
    }
  } catch (error) {
    console.error(`Error processing ${filePath}:`, error);
  }
});

console.log(`Modified ${modifiedCount} files`);
console.log("Cleanup complete!");
