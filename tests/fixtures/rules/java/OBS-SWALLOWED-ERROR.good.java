class Sample {
  void save(Data data) {
    try {
      write(data);
    } catch (IOException e) {
      log.error("save failed", e);
    }
    try {
      write(data);
    } catch (IOException e) {
      throw new IllegalStateException(e);
    }
    try {
      write(data);
    } catch (IOException e) {
      // the cache is optional
    }
    try {
      write(data);
    } catch (IOException e) {
      setSaveError(true);
    }
  }
}
