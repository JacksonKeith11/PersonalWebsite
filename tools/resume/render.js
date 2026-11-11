const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch(); const p = await b.newPage();
  await p.goto('file://' + __dirname + '/resume.html');
  await p.pdf({ path: __dirname + '/../../app/static/Jackson-Keith-Resume.pdf', preferCSSPageSize: true, printBackground: true });
  await b.close();
})();
