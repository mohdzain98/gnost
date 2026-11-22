class Sample {
  void work() {
    try {
      step();
    } catch (IOException e) {
      log.error("step failed", e);
    }
  }
}
