class Sample {
  void load() {
    try {
      risky();
    } catch (IOException e) {
      // the file may not exist yet, which is fine
    }
  }
}
