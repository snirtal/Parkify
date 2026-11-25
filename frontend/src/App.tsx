import { ParkingStateProvider } from './context/ParkingStateProvider'
import { AppRouter } from './router/AppRouter'

function App() {
  return (
    <ParkingStateProvider>
      <AppRouter />
    </ParkingStateProvider>
  )
}

export default App
