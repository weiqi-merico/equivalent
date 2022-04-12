var domain = 'http://172.26.129.137/';

async function setUp(context, commands) {
  await commands.navigate(
    domain
  );

  try {
    await commands.addText.byName('sigma@meri.co', 'username');
    await commands.addText.byName('himerico', 'password');
    await commands.click.byXpathAndWait("//button[@data-ga='login-button']")
    return commands.wait.byTime(5000);
  } catch (e) {
    throw e;
  }
};

async function perfTest(context, commands) {
  // add your own code here
  await commands.measure.start(domain + 'dashboard/v3/projects-performance/group/91a2ccb3-71a5-42ac-b296-f2c626ad4bf7/dev-equivalent?filterKey=3a58d7ca8833d11367502d5ca1b5a043');
  return await commands.measure.start(domain + 'dashboard/v3/teams-performance/0ee06f9e-f7cd-4d3c-b8ff-198212e49064/dev-equivalent?filterKey=845a97d6cc272a0de29a204e6fba469b');
};

// async function tearDown(context, commands) {
//   // do some cleanup here
// };

module.exports = {
  setUp: setUp,
  // tearDown: tearDown,
  test: perfTest
};
