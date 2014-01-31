using System;

namespace KinectBats
{
#if WINDOWS || XBOX
    static class Program
    {
        /// <summary>
        /// The main entry point for the application.
        /// </summary>
        static void Main(string[] args)
        {
            using (KinectBats game = new KinectBats())
            {
                game.Run();
            }
        }
    }
#endif
}

