package demo;

import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/greet")
public class GreetingController {

    @GetMapping("/{name}")
    public String greet(@PathVariable String name) {
        return "hi " + name;
    }

    @PostMapping(value = {"/a", "/b"}, consumes = "application/json")
    public void create() {}

    @RequestMapping(value = "/x", method = RequestMethod.PUT)
    @ResponseBody
    public String update() {
        return "";
    }
}
