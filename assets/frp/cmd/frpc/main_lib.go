//main_lib.go)
package main

import "C"
import (
	"os"

	_ "github.com/fatedier/frp/assets/frpc"
	"github.com/fatedier/frp/cmd/frpc/sub"
)

//export StartFrpcService
func StartFrpcService(configLocation *C.char) {
	// 这个函数现在是阻塞的，它会一直运行直到frp结束
	goConfigLocation := C.GoString(configLocation)

	os.Args = []string{
		"frpc", // 程序名可以硬编码
		"-c",
		goConfigLocation,
	}

	sub.Execute()
}

func main() {}
