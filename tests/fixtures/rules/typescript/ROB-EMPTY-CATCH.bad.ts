function load() {
  try {
    risky();
  } 
  // expect: ROB-EMPTY-CATCH
  catch (err) {}
}

// expect: ROB-EMPTY-CATCH
fetchData().catch(() => {});
