const fs = require('fs');
const path = 'frontend/src/views/WallstreetTestView.vue';
let content = fs.readFileSync(path, 'utf8');
content = content.replace('from "../api/wallstreetcn"', 'from "@/news/api/wallstreet"');
fs.writeFileSync(path, content, 'utf8');
console.log('Import fixed');
