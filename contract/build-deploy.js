const fs = require('fs');
const path = require('path');
const PROJ = '/home/hatch/workspace/projects/talvio-generate/contract';
const abi = fs.readFileSync(path.join(PROJ, 'TalvioGenerate.abi.json'), 'utf8').trim();
const bytecode = fs.readFileSync(path.join(PROJ, 'TalvioGenerate.creation.txt'), 'utf8').trim();
let html = fs.readFileSync(path.join(PROJ, 'deploy.template.html'), 'utf8');
if (!html.includes('__ABI__') || !html.includes('__BYTECODE__')) { console.error('placeholders missing'); process.exit(1); }
html = html.replace('__ABI__', abi).replace('__BYTECODE__', bytecode);
fs.writeFileSync(path.join(PROJ, 'deploy.html'), html);
console.log('deploy.html written:', html.length, 'bytes');
