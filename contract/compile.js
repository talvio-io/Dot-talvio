const fs = require('fs');
const path = require('path');
const solc = require('/home/hatch/workspace/tmp-check/acs-solc/node_modules/solc');

const PROJ = '/home/hatch/workspace/projects/talvio-generate/contract';
// OpenZeppelin 5.4.0 sources (same build env as the DOT token kit)
const OZ = '/home/hatch/workspace/projects/ascension-catty/build-env/node_modules';
const file = 'TalvioGenerate.sol';
const source = fs.readFileSync(path.join(PROJ, file), 'utf8');

function findImports(importPath) {
  try {
    return { contents: fs.readFileSync(path.join(OZ, importPath), 'utf8') };
  } catch (e) {
    return { error: 'not found: ' + importPath };
  }
}

const input = {
  language: 'Solidity',
  sources: { [file]: { content: source } },
  settings: {
    evmVersion: 'paris',
    optimizer: { enabled: true, runs: 200 },
    outputSelection: { '*': { '*': ['abi', 'evm.bytecode', 'evm.deployedBytecode'] } }
  }
};

const output = JSON.parse(solc.compile(JSON.stringify(input), { import: findImports }));
const errors = (output.errors || []).filter(e => e.severity === 'error');
const warnings = (output.errors || []).filter(e => e.severity === 'warning');
if (errors.length) { console.error('ERRORS:', errors.map(e => e.formattedMessage)); process.exit(1); }
console.log('solc:', solc.version());
console.log('warnings:', warnings.length);
warnings.forEach(w => console.log(w.formattedMessage));
const c = output.contracts[file]['TalvioGenerate'];
fs.writeFileSync(path.join(PROJ, 'TalvioGenerate.abi.json'), JSON.stringify(c.abi, null, 2));
fs.writeFileSync(path.join(PROJ, 'TalvioGenerate.creation.txt'), c.evm.bytecode.object);
fs.writeFileSync(path.join(PROJ, 'TalvioGenerate.runtime.txt'), c.evm.deployedBytecode.object);
console.log('creation bytes:', c.evm.bytecode.object.length / 2, '| runtime bytes:', c.evm.deployedBytecode.object.length / 2);
