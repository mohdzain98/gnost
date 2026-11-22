class Sample {
  void save(Data data) {
    try {
      write(data);
    }
    // expect: OBS-SWALLOWED-ERROR
    catch (IOException e) {
      count += 1;
    }
  }
}
