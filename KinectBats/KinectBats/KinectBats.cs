using System;
using System.Collections.Generic;
using System.Linq;
using System.Diagnostics;

using Microsoft.Xna.Framework;
using Microsoft.Xna.Framework.Audio;
using Microsoft.Xna.Framework.Content;
using Microsoft.Xna.Framework.GamerServices;
using Microsoft.Xna.Framework.Graphics;
using Microsoft.Xna.Framework.Input;
using Microsoft.Xna.Framework.Media;

using Microsoft.Kinect;

namespace KinectBats
{
    /// <summary>
    /// This is the main type for your game
    /// </summary>
    public class KinectBats : Microsoft.Xna.Framework.Game
    {
        GraphicsDeviceManager graphics;
        SpriteBatch spriteBatch;
        KinectSensor kinect;
        Texture2D colorVideo, depthVideo;
        Boolean debugging = true;
        Boolean done = false;
        const int skeletonCount = 6;
        Skeleton[] allSkeletons = new Skeleton[skeletonCount];
        CoordinateMapper cm;

        Texture2D marker;

        ColorImagePoint headColorPoint;
        ColorImagePoint leftColorPoint;
        ColorImagePoint rightColorPoint;

        const DepthImageFormat depthFormat = DepthImageFormat.Resolution320x240Fps30;
        const ColorImageFormat colorFormat = ColorImageFormat.RgbResolution640x480Fps30;

        public KinectBats()
        {
            graphics = new GraphicsDeviceManager(this);
            Content.RootDirectory = "Content";
        }

        /// <summary>
        /// Allows the game to perform any initialization it needs to before starting to run.
        /// This is where it can query for any required services and load any non-graphic
        /// related content.  Calling base.Initialize will enumerate through any components
        /// and initialize them as well.
        /// </summary>
        protected override void Initialize()
        {
            
            try
            {
                if (KinectSensor.KinectSensors.Count > 0)
                {
                    //Initialise Kinect
                    kinect = KinectSensor.KinectSensors[0];

                    if (kinect.Status == KinectStatus.Connected)
                    {
                        kinect.ColorStream.Enable(colorFormat);
                        kinect.DepthStream.Enable(depthFormat);
                        kinect.SkeletonStream.Enable();

                        kinect.AllFramesReady += new EventHandler<AllFramesReadyEventArgs>(kinect_AllFramesReady);

                        kinect.Start();

                        cm = new CoordinateMapper(kinect);
                        Debug.WriteLineIf(debugging, kinect.Status);

                        
                    }

                    
                }
            }
            catch (Exception e)
            {
                Debug.WriteLine(e.ToString());
            }

            base.Initialize();


        }

        private byte[] ConvertDepthFrame(short[] depthFrame, DepthImageStream depthStream)
        {
            int RedIndex = 0, GreenIndex = 1, BlueIndex = 2, AlphaIndex = 3;

            byte[] depthFrame32 = new byte[depthStream.FrameWidth * depthStream.FrameHeight * 4];

            for (int i16 = 0, i32 = 0; i16 < depthFrame.Length && i32 < depthFrame32.Length; i16++, i32 += 4)
            {
                int player = depthFrame[i16] & DepthImageFrame.PlayerIndexBitmask;
                int realDepth = depthFrame[i16] >> DepthImageFrame.PlayerIndexBitmaskWidth;

                // transform 13-bit depth information into an 8-bit intensity appropriate
                // for display (we disregard information in most significant bit)
                byte intensity = (byte)(~(realDepth >> 4));

                depthFrame32[i32 + RedIndex] = (byte)(intensity);
                depthFrame32[i32 + GreenIndex] = (byte)(intensity);
                depthFrame32[i32 + BlueIndex] = (byte)(intensity);
                depthFrame32[i32 + AlphaIndex] = 255;
            }
            return depthFrame32;
        }

        void kinect_AllFramesReady(object sender, AllFramesReadyEventArgs imageFrames)
        {
            if (done)
            {
                return;
            }

            kinect_ColorFrameReady(sender, imageFrames);
            Skeleton s = GetFirstSkeleton(imageFrames);
            if (s != null)
            {
                GetCameraPoint(s, imageFrames);
            }
        }

        void kinect_ColorFrameReady(object sender, AllFramesReadyEventArgs imageFrames)
        {
            //Get raw image
            ColorImageFrame colorVideoFrame = imageFrames.OpenColorImageFrame();

            if (colorVideoFrame != null)
            {
                //Create array for pixel data and copy it from the image frame
                Byte[] pixelData = new Byte[colorVideoFrame.PixelDataLength];
                colorVideoFrame.CopyPixelDataTo(pixelData);

                //Convert RGBA to BGRA
                Byte[] bgraPixelData = new Byte[colorVideoFrame.PixelDataLength];
                for (int i = 0; i < pixelData.Length; i += 4)
                {
                    bgraPixelData[i] = pixelData[i + 2];
                    bgraPixelData[i + 1] = pixelData[i + 1];
                    bgraPixelData[i + 2] = pixelData[i];
                    bgraPixelData[i + 3] = (Byte)255; //The video comes with 0 alpha so it is transparent
                }

                // Create a texture and assign the realigned pixels
                colorVideo = new Texture2D(graphics.GraphicsDevice, colorVideoFrame.Width, colorVideoFrame.Height);
                colorVideo.SetData(bgraPixelData);

                colorVideoFrame.Dispose();
            }

            
        }

        void GetCameraPoint(Skeleton s, AllFramesReadyEventArgs e)
        {
            using (DepthImageFrame depth = e.OpenDepthImageFrame())
            {
                if (depth == null || kinect == null)
                {
                    return;
                }

                //DepthImagePoint headDepthPoint = depth.MapFromSkeletonPoint(s.Joints[JointType.Head].Position);
                //DepthImagePoint headDepthPoint = cm.MapDepthPointToColorPoint(s.Joints[JointType.Head].Position, );
                
                DepthImagePoint headDepthPoint = cm.MapSkeletonPointToDepthPoint(s.Joints[JointType.Head].Position, depthFormat);
                DepthImagePoint leftDepthPoint = cm.MapSkeletonPointToDepthPoint(s.Joints[JointType.HandLeft].Position, depthFormat);
                DepthImagePoint rightDepthPoint = cm.MapSkeletonPointToDepthPoint(s.Joints[JointType.HandRight].Position, depthFormat);

                headColorPoint = cm.MapDepthPointToColorPoint(depthFormat, headDepthPoint, colorFormat);
                leftColorPoint = cm.MapDepthPointToColorPoint(depthFormat, leftDepthPoint, colorFormat);
                rightColorPoint = cm.MapDepthPointToColorPoint(depthFormat, rightDepthPoint, colorFormat);
            }
        }

        Skeleton GetFirstSkeleton(AllFramesReadyEventArgs e)
        {
            using (SkeletonFrame frame = e.OpenSkeletonFrame())
            {
                if (frame == null)
                {
                    return null;
                }

                frame.CopySkeletonDataTo(allSkeletons);

                Skeleton first = (from s in allSkeletons where s.TrackingState == SkeletonTrackingState.Tracked select s).FirstOrDefault();
                Console.WriteLine(first);
                return first;
            }
        }

        /// <summary>
        /// LoadContent will be called once per game and is the place to load
        /// all of your content.
        /// </summary>
        protected override void LoadContent()
        {
            // Create a new SpriteBatch, which can be used to draw textures.
            spriteBatch = new SpriteBatch(GraphicsDevice);

            // TODO: use this.Content to load your game content here
            marker = this.Content.Load<Texture2D>("marker");
        }

        /// <summary>
        /// UnloadContent will be called once per game and is the place to unload
        /// all content.
        /// </summary>
        protected override void UnloadContent()
        {
            // TODO: Unload any non ContentManager content here
        }

        /// <summary>
        /// Allows the game to run logic such as updating the world,
        /// checking for collisions, gathering input, and playing audio.
        /// </summary>
        /// <param name="gameTime">Provides a snapshot of timing values.</param>
        protected override void Update(GameTime gameTime)
        {
            // Allows the game to exit
            if ((Keyboard.GetState(PlayerIndex.One).IsKeyDown(Keys.Escape)) || (GamePad.GetState(PlayerIndex.One).Buttons.Back == ButtonState.Pressed))
                this.Exit();

            // TODO: Add your update logic here

            base.Update(gameTime);


        }

        /// <summary>
        /// This is called when the game should draw itself.
        /// </summary>
        /// <param name="gameTime">Provides a snapshot of timing values.</param>
        protected override void Draw(GameTime gameTime)
        {
            GraphicsDevice.Clear(Color.CornflowerBlue);

            // Draw RGB video
            if (colorVideo != null)
            {
                spriteBatch.Begin();
                spriteBatch.Draw(colorVideo, new Rectangle(0, 0, 640, 480), Color.White);
                spriteBatch.Draw(marker, new Rectangle(headColorPoint.X, headColorPoint.Y, 32, 32), Color.White);
                spriteBatch.End();
            }

            base.Draw(gameTime);
        }

        void StopKinect(KinectSensor sensor)
        {
            if (sensor == null)
            {
                return;
            }

            if (sensor.SkeletonStream.IsEnabled)
            {
                sensor.SkeletonStream.Disable();
            }

            if (sensor.ColorStream.IsEnabled)
            {
                sensor.ColorStream.Disable();
            }

            if (sensor.DepthStream.IsEnabled)
            {
                sensor.DepthStream.Disable();
            }

            // detach event handlers
            sensor.AllFramesReady -= this.kinect_AllFramesReady;

            try
            {
                sensor.Stop();
            }
            catch (Exception e)
            {
                Debug.WriteLine("unknown Exception {0}", e.Message);
            }
        }

        protected override void OnExiting(Object sender, EventArgs args)
        {
            done = true;

            StopKinect(kinect);

            base.OnExiting(sender, args);
        }

    }
}


