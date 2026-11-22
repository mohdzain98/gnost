class Sample {
  void load() {
    try {
      risky();
    } catch (IOException | IllegalStateException e) {
      log.error("failed", e);
    }
  }
}
