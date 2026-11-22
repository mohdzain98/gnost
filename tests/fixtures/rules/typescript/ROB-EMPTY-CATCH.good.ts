function load() {
  try {
    risky();
  } catch (err) {
    // the file may not exist yet, which is fine
  }
}

fetchData().catch((err) => handle(err));
