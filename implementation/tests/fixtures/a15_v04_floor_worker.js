'use strict';
// Disposable test-only subprocess. Loads synthetic fixture keys; never a deployed service.
const fs = require('node:fs');
const path = require('node:path');
const floor = require('../../research/a15_external_floor_simulator_v0_4.js');
const [labDir, stage, requestFile = 'test-only-request.json'] = process.argv.slice(2);
if(!labDir)process.exit(2);
const config=JSON.parse(fs.readFileSync(path.join(labDir,'test-only-config.json'),'utf8'));
if(stage)config.testOnlyFaultHook=s=>{if(s===stage)process.exit(73);};
const request=JSON.parse(fs.readFileSync(path.join(labDir,requestFile),'utf8'));
const reply=floor.openFloor(path.join(labDir,'floor'),config).advance(request);
process.stdout.write(JSON.stringify(reply)+'\n');
