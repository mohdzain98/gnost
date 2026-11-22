class Sample {
  void load() {
    try {
      risky();
    }
    // expect: ROB-CATCH-GENERIC
    catch (Exception e) {
      log.error("failed", e);
    }
  }
}
